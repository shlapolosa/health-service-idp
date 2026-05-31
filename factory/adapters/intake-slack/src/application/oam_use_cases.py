"""Application layer use cases for OAM webhook processing.

This module contains the application-specific use cases for handling
OAM webhook requests, following the onion architecture pattern.
"""

from typing import Dict, Any
import logging

from ..domain.models import (
    OAMApplication, 
    OAMComponent, 
    OAMWebhookRequest,
    OAMWebhookResponse
)
from ..domain.services import OAMWebhookService

logger = logging.getLogger(__name__)


class ProcessOAMWebhook:
    """Use case for processing OAM webhook requests.
    
    This class orchestrates the processing of OAM webhook requests,
    coordinating between the domain service and infrastructure layers.
    """
    
    def __init__(self, argo_client):
        """Initialize with infrastructure dependencies.
        
        Args:
            argo_client: ArgoClient from infrastructure layer
        """
        self.argo_client = argo_client
        self.service = OAMWebhookService()
    
    def execute(self, admission_request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the OAM webhook processing use case.
        
        Args:
            admission_request: Raw admission request from Kubernetes
            
        Returns:
            Admission response for Kubernetes
        """
        try:
            # Parse the admission request
            request = self._parse_admission_request(admission_request)
            
            # Process through domain service
            response = self.service.process_oam_webhook(request, self.argo_client)
            
            # Convert to admission response
            return self._build_admission_response(response)
            
        except Exception as e:
            logger.error(f"Error processing OAM webhook: {str(e)}")
            # Always allow to avoid blocking deployments
            return {
                "apiVersion": "admission.k8s.io/v1",
                "kind": "AdmissionReview",
                "response": {
                    "uid": admission_request.get("request", {}).get("uid", "unknown"),
                    "allowed": True,
                    "status": {
                        "message": f"Error processing webhook: {str(e)}"
                    }
                }
            }
    
    def _parse_admission_request(self, admission_request: Dict[str, Any]) -> OAMWebhookRequest:
        """Parse Kubernetes admission request into domain model.
        
        Args:
            admission_request: Raw admission request
            
        Returns:
            OAMWebhookRequest domain model
        """
        request = admission_request.get("request", {})
        oam_object = request.get("object", {})
        
        # Parse components
        components = []
        for comp_data in oam_object.get("spec", {}).get("components", []):
            component = OAMComponent(
                name=comp_data.get("name", ""),
                type=comp_data.get("type", ""),
                properties=comp_data.get("properties", {}),
                traits=comp_data.get("traits", [])
            )
            components.append(component)
        
        # Create OAM Application
        oam_app = OAMApplication(
            name=oam_object.get("metadata", {}).get("name", ""),
            namespace=oam_object.get("metadata", {}).get("namespace", "default"),
            components=components,
            policies=oam_object.get("spec", {}).get("policies", []),
            labels=oam_object.get("metadata", {}).get("labels", {}),
            annotations=oam_object.get("metadata", {}).get("annotations", {})
        )
        
        # Create webhook request
        return OAMWebhookRequest(
            uid=request.get("uid", ""),
            operation=request.get("operation", ""),
            oam_application=oam_app,
            dry_run=request.get("dryRun", False)
        )
    
    def _build_admission_response(self, response: OAMWebhookResponse) -> Dict[str, Any]:
        """Build Kubernetes admission response from domain response.
        
        Args:
            response: Domain response model
            
        Returns:
            Kubernetes admission response
        """
        admission_response = {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "uid": response.uid,
                "allowed": response.allowed
            }
        }
        
        # Add status message if present
        if response.message or response.triggered_workflows:
            status_message = response.message or ""
            if response.triggered_workflows:
                status_message += f" Triggered: {', '.join(response.triggered_workflows)}"
            
            admission_response["response"]["status"] = {
                "message": status_message
            }
        
        return admission_response