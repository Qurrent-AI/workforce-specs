#! /usr/bin/env python3

import argparse
import asyncio

from qurrent.evaluations.runner import EvalRunner

parser = argparse.ArgumentParser()
parser.add_argument(
    "--workflow-instance-id",
    type=str,
    required=True,
    help="Workflow instance ID to evaluate",
)
parser.add_argument("--env", type=str, default="dev", help="Environment (default: dev)")
args = parser.parse_args()

WORKFLOW_INSTANCE_ID = args.workflow_instance_id
ENV = args.env


async def main():

    eval_runner = EvalRunner(workflow_instance_id=WORKFLOW_INSTANCE_ID, environment=ENV)

    # This is an example of a custom evaluation metric.
    criteria = """
        Check if the output contains the phrase 'Hello world!' and nothing else.
        If so, it passes, otherwise it fails.
    """

    eval_runner.add_custom_evaluation_metric(
        name="Demo Metric", criteria=criteria, eval_final_completion_only=True
    )

    await eval_runner.run(
        save_results=False,  # Set to True to save the results to the database
    )


if __name__ == "__main__":
    print("*" * 100)
    print(f"Creating dataframe for workflow instance: {WORKFLOW_INSTANCE_ID}")
    print(f"Environment: {ENV}")
    print("*" * 100)
    asyncio.run(main())
