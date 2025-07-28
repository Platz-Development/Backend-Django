
import logging
from users.models import UniversityDomain

uni_email_validator_logger = logging.getLogger("UniEmailValidator")

def extract_email_domain(email: str) -> str | None:
    
    if not email or '@' not in email:
        return None

    try:
        domain = email.split('@')[1].strip().lower()

        # Fetch all known university domains
        from users.models import UniversityDomain
        known_domains = list(UniversityDomain.objects.filter(is_active=True).values_list('domain', flat=True))

        # Match by suffix
        for allowed_domain in known_domains:
            if domain.endswith(allowed_domain):
                return allowed_domain
        return None
    except Exception as e:
        uni_email_validator_logger.error(f"Base Domain Extraction Failed For Email '{email}': {e}")
        return None


def get_university_discount_from_email(email: str) -> int:
    
    domain = extract_email_domain(email)
    if not domain:
        return 0

    try:
        uni = UniversityDomain.objects.get(domain=domain, is_active=True)
        return uni.discount_percent
    except UniversityDomain.DoesNotExist:
        return 0
    except Exception as e:
        uni_email_validator_logger.error(f"Error In get_university_discount_from_email For '{email}': {e}")
        return 0


def get_commission_rate_for_tutor(email: str) -> int:
    
    domain = extract_email_domain(email)
    if not domain:
        return 20

    try:
        return 0 if UniversityDomain.objects.filter(domain=domain, is_active=True).exists() else 20
    except Exception as e:
        uni_email_validator_logger.error(f"Error In get_commission_rate_for_tutor For '{email}': {e}")
        return 20
