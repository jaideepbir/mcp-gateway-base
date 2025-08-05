# MCP Gateway Architecture Diagram
# Generates a detailed architecture with two environments: Local Docker Compose and Production GCP.
# Requires: pip install diagrams && Graphviz installed.
# Output: mcp_gateway_architecture.png in the same directory.

from diagrams import Cluster, Diagram, Edge
from diagrams.onprem.client import Users
from diagrams.onprem.auth import Oauth2Proxy as OAuth2ProviderIcon
from diagrams.onprem.network import Nginx as HTTPSLBIcon
from diagrams.onprem.container import Docker
from diagrams.onprem.iac import Terraform
from diagrams.onprem.security import Vault as SecretManagerIcon
from diagrams.onprem.logging import Loki as CloudLoggingIcon
from diagrams.onprem.monitoring import Grafana as CloudMonitoringIcon
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.compute import Server
from diagrams.custom import Custom

# Kubernetes / GKE
from diagrams.k8s.compute import Pod
from diagrams.k8s.network import Ingress, Service
from diagrams.k8s.ecosystem import Helm
from diagrams.k8s.podconfig import CM as K8sConfigMap, Secret as K8sSecret

# GCP icons
from diagrams.gcp.network import LoadBalancing
from diagrams.gcp.compute import GKE
from diagrams.gcp.database import SQL
from diagrams.gcp.storage import GCS
from diagrams.gcp.devtools import SourceRepositories as ArtifactRegistryIcon  # closest available
from diagrams.onprem.ci import GithubActions as CloudBuild  # stand-in for GCP Cloud Build
from diagrams.gcp.security import KMS
from diagrams.gcp.operations import Monitoring as GcpMonitoring, Logging as GcpLogging
from diagrams.onprem.security import Vault as Iam  # stand-in for GCP IAM
from diagrams.gcp.network import VPC

# On-prem/on-container gateway & opa custom nodes (since diagrams has no MCP Gateway/OPA icon)
# You may replace these with official icons by providing local images and using Custom().
MCP_GATEWAY_LABEL = "MCP Gateway"
OPA_LABEL = "Open Policy Agent (OPA)"
TOOLS_LABEL = "MCP Tools (Tool Providers)"
IDP_LABEL = "IdP / Dev Auth-Server"
JWKS_LABEL = "JWKS"

graph_attr = {
    "fontsize": "22",
    "bgcolor": "white",
    "pad": "0.4",
}

node_attr = {
    "fontsize": "14"
}

edge_attr = {
    "fontsize": "12"
}

with Diagram(
    "MCP Gateway - Local & GCP Architecture",
    show=False,
    filename="mcp_gateway_architecture",
    outformat=["png"],
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr,
    direction="LR",
):
    # Client and OAuth2 provider (shared conceptual actors)
    client = Users("Client (User/App)")
    oauth2 = OAuth2ProviderIcon(IDP_LABEL)

    # ==== Local Environment (Docker Compose) ====
    with Cluster("Local Docker Compose Stack"):
        # Local config sources
        local_env = Docker(".env")
        local_policies = Docker("policies/authz.rego")

        # Containers (use generic server icons to represent mcp-gateway and opa)
        mcp_gateway_local = Server(MCP_GATEWAY_LABEL)
        opa_local = Server(OPA_LABEL)
        db_local = PostgreSQL("PostgreSQL (Tool Call History & Auditing)")
        tools_local = Server(TOOLS_LABEL)

        # Show config feeds
        local_env >> Edge(color="gray", style="dotted", label="reads env") >> mcp_gateway_local
        local_policies >> Edge(color="gray", style="dotted", label="mounts policies") >> opa_local

        # Local interactions
        client >> Edge(color="darkgreen", label="API Request (Bearer Token)") >> mcp_gateway_local
        client << Edge(color="darkgreen", style="dashed", label="AuthN: Token via OAuth2") << oauth2

        mcp_gateway_local >> Edge(color="black", label="AuthZ: context -> decision") >> opa_local
        mcp_gateway_local >> Edge(color="darkorange", label="Tool Execution") >> tools_local
        mcp_gateway_local >> Edge(color="slateblue", label="Auditing") >> db_local

        # JWKS validation flow (local gateway to IdP)
        mcp_gateway_local << Edge(color="gray", style="dashed", label="JWKS fetch for validation") << oauth2

    # ==== Production GCP Environment ====
    with Cluster("GCP Project"):
        # Ingress/Load Balancer
        https_lb = LoadBalancing("HTTPS Load Balancer")

        # Networking and IAM
        vpc = VPC("VPC (Private IP)")
        iam = Iam("IAM (Service Accounts / WI)")
        kms = KMS("KMS (optional)")

        # GKE
        with Cluster("GKE Cluster"):
            # Indicate config/secret injection at cluster level
            k8s_cm = K8sConfigMap("ConfigMap")
            k8s_secret = K8sSecret("K8s Secret")

            mcp_gateway_gke = Pod(MCP_GATEWAY_LABEL)
            opa_gke = Pod(OPA_LABEL)
            tools_gke = Pod(TOOLS_LABEL)

            # Internal service exposure (optional)
            gw_svc = Service("Gateway SVC")
            opa_svc = Service("OPA SVC")

            https_lb >> Edge(color="darkgreen", label="HTTPS") >> gw_svc >> mcp_gateway_gke
            opa_svc >> opa_gke

            # Config applied inside cluster
            k8s_cm >> Edge(color="gray", style="dotted", label="config") >> mcp_gateway_gke
            k8s_secret >> Edge(color="gray", style="dotted", label="secrets") >> mcp_gateway_gke

        # Cloud SQL for Postgres
        cloud_sql = SQL("Cloud SQL (PostgreSQL)\nPrivate IP")

        # Secret Manager & GCS policy bundles
        secret_mgr = SecretManagerIcon("Secret Manager")
        gcs_policies = GCS("GCS Bucket (OPA Policy Bundles)")

        # Telemetry
        cloud_logging = GcpLogging("Cloud Logging")
        cloud_monitoring = GcpMonitoring("Cloud Monitoring")

        # Artifact build (CI/CD context)
        cloud_build = CloudBuild("Cloud Build / CI")
        artifact_reg = ArtifactRegistryIcon("Artifact Registry")

        # OAuth flows (same IdP, could be external)
        # Client token + gateway JWKS validation
        client >> Edge(color="darkgreen", label="API Request (Bearer Token)") >> https_lb
        client << Edge(color="darkgreen", style="dashed", label="AuthN: Token via OAuth2") << oauth2
        mcp_gateway_gke << Edge(color="gray", style="dashed", label="JWKS fetch for validation") << oauth2

        # Authorization path within GKE
        mcp_gateway_gke >> Edge(color="black", label="AuthZ: context -> decision") >> opa_gke

        # Tool execution within cluster
        mcp_gateway_gke >> Edge(color="darkorange", label="Tool Execution") >> tools_gke

        # Auditing to Cloud SQL over private IP
        vpc >> Edge(color="gray", style="dotted") >> cloud_sql
        mcp_gateway_gke >> Edge(color="slateblue", label="Auditing") >> cloud_sql

        # Config/Secrets to cluster
        secret_mgr >> Edge(color="gray", style="dotted", label="creds/secrets") >> k8s_secret
        gcs_policies >> Edge(color="gray", style="dotted", label="OPA bundles") >> opa_gke

        # Telemetry export
        mcp_gateway_gke >> Edge(color="purple", style="dashed", label="logs/metrics") >> cloud_logging
        mcp_gateway_gke >> Edge(color="purple", style="dashed") >> cloud_monitoring
        opa_gke >> Edge(color="purple", style="dashed") >> cloud_logging
        opa_gke >> Edge(color="purple", style="dashed") >> cloud_monitoring

        # CI/CD to artifact registry and cluster (conceptual)
        cloud_build >> Edge(color="gray", style="dotted", label="push images") >> artifact_reg
        artifact_reg >> Edge(color="gray", style="dotted", label="pull deploy") >> mcp_gateway_gke
        iam >> Edge(color="gray", style="dotted", label="W/I, SAs, IAM") >> mcp_gateway_gke
        kms >> Edge(color="gray", style="dotted", label="optional KMS") >> secret_mgr
