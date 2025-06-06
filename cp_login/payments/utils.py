from decimal import Decimal, ROUND_HALF_UP
import re , uuid

def calculate_cp_profit_from_learner(amount_received_at_stripe: float, base_price: float) -> float:
    
    amount_received = Decimal(str(amount_received_at_stripe))
    tutor_base_price = Decimal(str(base_price))
    profit = amount_received - tutor_base_price

    return float(profit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def calculate_commission_and_payout_for_tutor(commission_rate, course_price: float) -> dict:
    
    course_price_decimal = Decimal(str(course_price))
    commission_rate = Decimal(str(commission_rate)) / Decimal("100")

    commission = course_price_decimal * commission_rate
    tutor_payout = course_price_decimal - commission

    return {
        "commission_from_tutor": float(commission.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "tutor_payout": float(tutor_payout.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    }
