from enum import Enum


class SourceType(str, Enum):
    RFC = "rfc"
    NIST = "nist"
    CIS = "cis"
    ISO = "iso"
    VENDOR_DOC = "vendor_doc"
    STACK_OVERFLOW = "stack_overflow"
    REDDIT = "reddit"
    GITHUB_ISSUE = "github_issue"
    CVE = "cve"
    BLOG = "blog"
    SYNTHETIC = "synthetic"
    SYNTHETIC_LOOP = "synthetic_loop"


class Domain(str, Enum):
    LDAP = "ldap"
    SAML = "saml"
    OAUTH = "oauth"
    OIDC = "oidc"
    SCIM = "scim"
    KERBEROS = "kerberos"
    WEBAUTHN_FIDO = "webauthn_fido"
    ACTIVE_DIRECTORY = "active_directory"
    AZURE_AD_ENTRA = "azure_ad_entra"
    AWS_IAM = "aws_iam"
    GCP_IAM = "gcp_iam"
    OKTA = "okta"
    SSO_FEDERATION = "sso_federation"
    IGA_PROVISIONING = "iga_provisioning"
    PAM = "pam"
    NHI = "nhi"
    AI_AGENT_IDENTITY = "ai_agent_identity"
    MFA = "mfa"
    ZERO_TRUST = "zero_trust"
    COMPLIANCE = "compliance"


class TaskType(str, Enum):
    EXPLAIN_CONCEPT = "explain_concept"
    ANSWER_QUESTION = "answer_question"
    DIAGNOSE_PROBLEM = "diagnose_problem"
    PROVIDE_SOLUTION = "provide_solution"
    GENERATE_QUERY = "generate_query"
    ASSESS_RISK = "assess_risk"
    REVIEW_ACCESS = "review_access"
    MAP_COMPLIANCE = "map_compliance"
    AUDIT_CONFIG = "audit_config"
    PARSE_ASSERTION = "parse_assertion"
    EXPLAIN_FLOW = "explain_flow"
    REMEDIATE = "remediate"
