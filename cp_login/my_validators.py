from scheduling_stripe.serializers import TutorAvailabilityDisplaySerializer
from users.models import Availability

def validate_availabilities(selected_availability_ids, tutor, learner_timezone, tutor_timezone):
   
    all_selected = Availability.objects.filter(
        id__in=selected_availability_ids,
        tutor=tutor
    )
    
    valid_availabilities = all_selected.filter(is_booked=False)
    booked_availabilities = all_selected.filter(is_booked=True)
    

    existing_ids = set(all_selected.values_list('id', flat=True))
    invalid_availabilities = [
        {'id': id, 'status': 'Invalid availability slot'}
        for id in selected_availability_ids
        if id not in existing_ids
    ]
    
    def serialize_availabilities(queryset):
        return TutorAvailabilityDisplaySerializer(
            queryset,
            many=True,
            context={'learner_timezone': learner_timezone,'tutor_timezone': tutor_timezone}
        ).data
    
    return {
        'valid': serialize_availabilities(valid_availabilities),
        'booked': serialize_availabilities(booked_availabilities),
        'invalid': invalid_availabilities
    }
