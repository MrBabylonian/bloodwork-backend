import boto3
import time
from botocore.exceptions import BotoCoreError, ClientError  # noqa
from app.utils.logger_utils import Logger

logger = Logger.setup_logging().getChild("ec2_instance_controller")

INSTANCE_ID: str = "i-0476378924320e248"
AWS_REGION: str = "eu-north-1"


class Ec2Controller:
	def __init__(self, instance_id: str = INSTANCE_ID, aws_region: str = AWS_REGION) -> None:
		self.instance_id = instance_id
		self.aws_region = AWS_REGION
		self.ec2 = boto3.client("ec2", region_name=aws_region)


	def get_instance_public_ip(self, instance_id: str = INSTANCE_ID) -> str:
		ec2 = self.ec2
		response = ec2.describe_instances(InstanceIds=[instance_id])
		return response["Reservations"][0]["Instances"][0]["PublicIpAddress"]

	def get_instance_status(self, include_all=True):
		try:
			response = self.ec2.describe_instance_status(
				InstanceIds=[self.instance_id],
				IncludeAllInstances=include_all
			)
			return response
		except (BotoCoreError, ClientError) as error:
			logger.error(f"Failed to get instance status: {error}")
			return {"InstanceStatuses": []}

	def is_inference_instance_running(self, timeout: int = 360) -> bool:
		"""
		Checks the current state of the inference EC2 instance and starts it
		if it is stopped. Waits until the instance is running or timeout occurs.
		"""
		try:
			response = self.get_instance_status()
			instance_statuses = response.get("InstanceStatuses", [])

			if not instance_statuses:
				logger.info(f"Instance status check failed. Attempting to start {INSTANCE_ID}...")
			else:
				state = instance_statuses[0]["InstanceState"]["Name"]

				if state == "stopped":
					logger.info(f"Instance {INSTANCE_ID} is stopped. Starting it...")
				elif state == "running":
					logger.info(f"EC2 instance {INSTANCE_ID} is already running.")
					return True
				elif state in ["stopping"]:
					logger.info(f"Waiting for EC2 inference instance to stop...")
					while state in ["stopping"]:
						time.sleep(5)
						response = self.get_instance_status()
						instance_statuses = response.get("InstanceStatuses", [])
						state = instance_statuses[0]["InstanceState"]["Name"] if instance_statuses else None

			self.ec2.start_instances(InstanceIds=[INSTANCE_ID])
			logger.info(f"Starting EC2 instance {INSTANCE_ID}...")

			elapsed = 0
			while elapsed < timeout:
				status = self.get_instance_status(include_all=True)
				instance_statuses = status.get("InstanceStatuses", [])
				if not instance_statuses:
					logger.info(f"Instance status not available yet. Retrying...")
					time.sleep(5)
					elapsed += 5
					continue

				instance = instance_statuses[0]
				state = instance["InstanceState"]["Name"]
				system_status = instance["SystemStatus"]["Status"]
				instance_status = instance["InstanceStatus"]["Status"]

				logger.info(f"State: {state} | System: {system_status} | Instance: {instance_status}")

				if state == "running" and system_status == "ok" and instance_status == "ok":
					time.sleep(60)
					logger.info("EC2 instance is fully initialized and ready.")
					return True
				time.sleep(5)
				elapsed += 5

			raise TimeoutError("Timeout: EC2 instance did not start in time.")

		except (BotoCoreError, ClientError, IndexError) as error:
			raise RuntimeError(f"Failed to start EC2 instance: {error}")