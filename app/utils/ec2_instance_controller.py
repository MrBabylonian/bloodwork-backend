import boto3
import time
from botocore.exceptions import BotoCoreError, ClientError  # noqa
from app.utils.logger_utils import Logger

logger = Logger.setup_logging().getChild("ec2_instance_controller")

INSTANCE_ID: str = "i-0476378924320e248"
AWS_REGION: str = "eu-north-1"


def is_inference_instance_running(timeout: int = 360) -> None:
	"""
	Checks the current state of the inference EC2 instance and starts it
	if it is stopped. Waits until the instance is running or timeout occurs.
	"""
	ec2 = boto3.client("ec2", region_name = AWS_REGION)
	try:
		while True:
			response = ec2.describe_instance_status(
				InstanceIds = [INSTANCE_ID],
				IncludeAllInstances = True
			)
			state = response["InstanceStatuses"][0]["InstanceState"]["Name"]

			if state == "running":
				logger.info(f"EC2 instance {INSTANCE_ID} is already running.")
				break

			while state in ["stopping"]:
				logger.info(f"Waiting for EC2 inference instance to stop...")
				time.sleep(5)

			ec2.start_instances(InstanceIds = [INSTANCE_ID])
			logger.info(f"Starting EC2 instance {INSTANCE_ID}...")

			elapsed = 0
			while elapsed < timeout:
				status = ec2.describe_instance_status(
					InstanceIds = [INSTANCE_ID],
					IncludeAllInstances = True
				)
				instance_statuses = status.get("InstanceStatuses", [])
				if not instance_statuses:
					logger.info(f"Instance status not available yet. "
								f"Retrying...")
					time.sleep(5)
					elapsed += 5
					continue

				instance = instance_statuses[0]
				state = instance["InstanceState"]["Name"]
				system_status = instance["SystemStatus"]["Status"]
				instance_status = instance["InstanceStatus"]["Status"]

				logger.info(f"State: {state} | System: {system_status} | "
							f"Instance: {instance_status}")

				if state == "running" and system_status == "ok" and instance_status == "ok":
					time.sleep(60)
					logger.info("EC2 instance is fully initialized and ready.")
					break
				time.sleep(5)
				elapsed += 5

				raise TimeoutError("Timeout: EC2 instance did not start in time.")

	except (BotoCoreError, ClientError, IndexError) as error:
		raise RuntimeError(f"Failed to start EC2 instance: {error}")
