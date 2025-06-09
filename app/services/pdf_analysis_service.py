from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from fastapi import BackgroundTasks, HTTPException, UploadFile

from app.services.openai_service import OpenAIService
from app.utils.file_utils import FileConverter
from app.utils.logger_utils import Logger

logger = Logger.setup_logging().getChild("pdf_analysis_service")

PDF_UPLOADS_ROOT_DIRECTORY: Path = Path("data/blood_work_pdfs")
PDF_UPLOADS_ROOT_DIRECTORY.mkdir(parents=True, exist_ok=True)


class PdfAnalysisService:
    def __init__(self) -> None:
        self.openai_service = OpenAIService()
        self.uploads_directory = PDF_UPLOADS_ROOT_DIRECTORY

    async def analyze_with_openai(
            self,
            image_path_list: list[Path],
            upload_folder: Path,
            pdf_uuid: str
    ) -> None:
        """
            Run OpenAI analysis on the blood work images and save the output
        """
        try:
            logger.info(
                f"Running OpenAI analysis for blood work images for UUID {pdf_uuid}")

            openai_interpretation = await self.openai_service.interpret_bloodwork_via_openai(image_path_list)

            print(type(openai_interpretation))

            analysis_output_path: Path = upload_folder / "analysis_output.json"
            with open(analysis_output_path, "w", encoding="utf-8") as f:
                try:
                    f.write(openai_interpretation)
                except Exception as error:
                    logger.exception(
                        f"Failed to write OpenAI interpretation to file: {error}")
                    raise

            logger.info(
                f"OpenAI interpreation saved to {analysis_output_path}")
        except Exception as error:
            logger.exception(
                f"Failed to run or save OpenAI analysis for UUID: {pdf_uuid} Error: {error}"
            )
            raise

    async def analyze_uploaded_pdf_file_background(
            self,
            file: UploadFile,
            background_tasks: BackgroundTasks
    ) -> dict[str, str]:
        """
        Process an uploaded PDF file and run analysis in the background
        """
        tmp_path = None
        try:
            pdf_uuid: str = str(uuid4())
            upload_folder: Path = self.uploads_directory / pdf_uuid
            upload_folder.mkdir(parents=True, exist_ok=True)

            with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                content = await file.read()
                tmp.write(content)
                tmp_path = Path(tmp.name)

            logger.info(f"Received PDF. Temporary file created at {tmp_path}")

            image_path_list: list[Path] = FileConverter.convert_pdf_to_image_list(
                tmp_path,
                upload_folder,
                pdf_uuid
            )
            logger.info(f"Converted to {len(image_path_list)} image(s)")

            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

            # Run OpenAI analysis in the background
            background_tasks.add_task(
                self.analyze_with_openai,
                image_path_list,
                upload_folder,
                pdf_uuid
            )

            return {
                "pdf_uuid": pdf_uuid,
                "message": "Analisi in corso. Torna più tardi per vedere i risultati."
            }
        except Exception as error:
            logger.error(f"Failed to process PDF. Error: {error}")
            raise HTTPException(
                status_code=500, detail="Errore durante l'analisi")

        finally:
            if tmp_path and tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
