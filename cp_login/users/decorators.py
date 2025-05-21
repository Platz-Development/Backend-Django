# users/decorators.py

from django.http import JsonResponse
from functools import wraps

API_KEYS = {
    "LEARNER_SIGNUP": "LEARNER_SIGNUP_lnsu8291df",
    "TUTOR_SIGNUP": "TUTOR_SIGNUP_tnsu1841kd",
    "LEARNER_LOGIN": "LEARNER_LOGIN_lnlg28dkf2",
    "TUTOR_LOGIN": "TUTOR_LOGIN_tnlg920fks",
    "VERIFY_EMAIL": "VERIFY_EMAIL_emv2821ks",
    "FORGOT_PWD": "FORGOT_PWD_fp9181dd",
    "RESET_PWD": "RESET_PWD_rp828fsdf",
    "TUTOR_PROFILE_UPD": "TUTOR_PROFILE_UPD_tpupd1938sd",
    "TUTOR_CERT_DEL": "TUTOR_CERT_DEL_tcdd2819df",
    "TUTOR_AVAIL_DEL": "TUTOR_AVAIL_DEL_tad918dks",
    "TUTOR_ACC_DEL": "TUTOR_ACC_DEL_taccdel9281",
    "GOOGLE_SIGNUP": "GOOGLE_SIGNUP_a12gs8s1g8",
    "GOOGLE_LOGIN": "GOOGLE_LOGIN_lg91s2l1ks",
    "TOKEN_OBTAIN": "TOKEN_OBTAIN_239fjs9sdf",
    "TOKEN_REFRESH": "TOKEN_REFRESH_kdf02r8fd8",
}

def require_api_key(key_name):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            client_key = request.headers.get('X-API-KEY')
            expected_key = API_KEYS.get(key_name)
            if client_key != expected_key:
                return JsonResponse({'detail': 'Invalid or missing API Key'}, status=403)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
