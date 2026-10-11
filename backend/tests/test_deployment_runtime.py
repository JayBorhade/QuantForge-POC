"""Deployment endpoints must not claim runtime actions without a runtime."""

import asyncio
import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.api.routes.deployments import start_deployment, stop_deployment
from app.models.deployment import DeploymentStatus


class DeploymentRuntimeTests(unittest.TestCase):
    def test_start_does_not_fake_running_state_without_runtime(self):
        deployment = MagicMock(status=DeploymentStatus.PENDING)
        user = MagicMock(id=uuid.uuid4())
        with patch(
            "app.api.routes.deployments._get_deployment",
            new=AsyncMock(return_value=deployment),
        ):
            with self.assertRaises(HTTPException) as error:
                asyncio.run(start_deployment(uuid.uuid4(), user, AsyncMock()))

        self.assertEqual(error.exception.status_code, 501)
        self.assertEqual(deployment.status, DeploymentStatus.PENDING)

    def test_stop_does_not_fake_stopped_state_without_runtime(self):
        deployment = MagicMock(status=DeploymentStatus.RUNNING)
        user = MagicMock(id=uuid.uuid4())
        with patch(
            "app.api.routes.deployments._get_deployment",
            new=AsyncMock(return_value=deployment),
        ):
            with self.assertRaises(HTTPException) as error:
                asyncio.run(stop_deployment(uuid.uuid4(), user, AsyncMock()))

        self.assertEqual(error.exception.status_code, 501)
        self.assertEqual(deployment.status, DeploymentStatus.RUNNING)


if __name__ == "__main__":
    unittest.main()
