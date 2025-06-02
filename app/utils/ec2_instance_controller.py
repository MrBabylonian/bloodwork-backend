import boto3
import time
from botocore.exceptions import BotoCoreError, ClientError
from app.utils.logger_utils import Logger

logger = Logger.setup_logging().getChild("ec2_instance_controller")

INSTANCE_ID: str = "i-0476378924320e248"
AWS_REGION: str = "eu-north-1"


def ensure_inference_instance_is_running(timeout: int = 360) -> None:
	"""
	Checks the current state of the inference EC2 instance and starts it
	if it is stopped. Waits until the instance is running or timeout occurs.
	"""
	ec2 = boto3.client("ec2", region_name = AWS_REGION)

	try:
		response = ec2.describe_instance_status(
			InstanceIds = [INSTANCE_ID],
			IncludeAllInstances = True
		)
		state = response["InstanceStatuses"][0]["InstanceState"]["Name"]

		if state == "running":
			return  # Already running

		if state in ["stopping", "shutting-down"]:
			raise RuntimeError(f"Instance is shutting down ({state})")

		if state in ["stopped", "stopping"]:
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
					logger.info("EC2 instance is fully initialized and ready.")
					return
			time.sleep(5)
			elapsed += 5

		raise TimeoutError("Timeout: EC2 instance did not start in time.")

	except (BotoCoreError, ClientError, IndexError) as error:
		raise RuntimeError(f"Failed to start EC2 instance: {error}")
