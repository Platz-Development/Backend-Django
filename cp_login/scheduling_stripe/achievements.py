from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.mail import send_mail
from .models import Tutor,TutorLiveClassStats,TutorLiveClassProfile



class BadgeProgressView(APIView):
    
    BADGE_TIERS = {
        0: {'name': 'No Badge', 'classes': 0},
        1: {'name': 'Platz Emerger', 'classes': 5},
        2: {'name': 'Platz Scholar', 'classes': 25},
        3: {'name': 'Platz Master', 'classes': 50},
        4: {'name': 'Platz Legend', 'classes': 100}
    }

    def get(self, request, tutor_id):

        try:
            tutor = Tutor.objects.get(pk=tutor_id)
            
        except Tutor.DoesNotExist:
            return Response({'error': 'Tutor not found'}, status=404)
        
        try:
            live_class_profiles = TutorLiveClassProfile.objects.filter(tutor=tutor)
        except:
            return Response({'error': 'Live Class Profiles not found'}, status=404)
        
        responses = []
        for live_class_profile in live_class_profiles:
            stats = TutorLiveClassStats.objects.get(live_class_profile=live_class_profile)
            current_badge = stats.current_badge
            next_badge = current_badge + 1 if int(current_badge) < 4 else None
            
            if current_badge >= 0:
                response={
                'subject':live_class_profile.subject,
                'motivation': self._get_motivation_message(stats, current_badge),
                'current_badge': self.BADGE_TIERS[current_badge]['name']   ,
                'next_badge': self.BADGE_TIERS[next_badge]['name'],
                'classes_taught': stats.classes_taught,
                'progress_percent': int((stats.classes_taught / self.BADGE_TIERS[next_badge]['classes']) * 100 ) if next_badge else None
            }   
            responses.append(response)
        
        return Response(responses)

    
    def _get_motivation_message(self, stats, current_tier):
        messages = {
            0: f"Teach {5 - stats.classes_taught} more classes to earn your first badge!",
            1: f"Keep going! Just {25 - stats.classes_taught} more classes to Platz Scholar",
            2: f"Halfway to Platz Master! {50 - stats.classes_taught} more classes left",
            3: f"Almost legendary! {100 - stats.classes_taught} more classes until Platz Legend",
            4: "You've reached the highest tier! Share your knowledge with others"
        }
        return messages.get(current_tier)
    

class ClassCompletionView(APIView):
   
    BADGE_TIERS = {
        0: {'name': 'No Badge', 'classes': 0},
        1: {'name': 'Platz Emerger', 'classes': 5},
        2: {'name': 'Platz Scholar', 'classes': 25},
        3: {'name': 'Platz Master', 'classes': 50},
        4: {'name': 'Platz Legend', 'classes': 100}
    }

    def post(self, request,live_class_profile_id):
        
        
        
        try:
            live_class_profile = TutorLiveClassProfile.objects.get(pk=live_class_profile_id)
        except:
            return Response({'error': 'Live Class Profiles not found'}, status=404)
        try:
            tutor = live_class_profile.tutor
        except Tutor.DoesNotExist:
            return Response({'error': 'Tutor not found'}, status=404)
            
        stats = TutorLiveClassStats.objects.get(live_class_profile=live_class_profile)
        stats.classes_taught = 25
        #stats.save()

        current_badge = self._get_current_badge(stats.classes_taught - 1)
        next_badge = self._get_current_badge(stats.classes_taught)

        if next_badge > current_badge:
            self._send_badge_achieved_email(stats,tutor,current_badge)
        else:
            self._send_class_completion_email(stats,tutor,current_badge )

        return Response({'status': 'Class Completion E-Mail Succesfully Sent'})

    def _get_current_badge(self, classes):
        for badge, details in self.BADGE_TIERS.items():
            if classes < details['classes']:
                return badge - 1
        return 4  

    def _send_class_completion_email(self, stats,tutor, current_badge):
        next_badge = current_badge + 1 if current_badge < 4 else None
        classes_needed = self.BADGE_TIERS.get(next_badge, {}).get('classes', 0) - stats.classes_taught if next_badge is not None else 0
        
        send_mail(
            subject="Great class today!",
            message=f"""
            Hey {tutor.user.f_name.capitalize()}!!
            Your recent class was successfully completed!
            You Have now taught {stats.classes_taught} classes.\n
            {f"Just {classes_needed} more classes to reach {self.BADGE_TIERS.get(next_badge, {}).get('name', 'N/A')}!" if next_badge else "You've reached the highest badge tier!"}
            """,
            from_email="notifications@campusplatz.com",
            recipient_list=[tutor.user.email]
        )

    def _send_badge_achieved_email(self,stats, tutor,current_badge):
        next_badge = current_badge + 1 if current_badge < 4 else None
        badge_name = self.BADGE_TIERS[next_badge]['name']
        send_mail(
            subject=f"🎉 next Badge Achieved: {badge_name}!",
            message=f"""
            Congratulations {tutor.user.f_name.capitalize()}!!\n\n
            You've earned the {badge_name} badge by teaching {stats.classes_taught} classes.
            Your dedication is inspiring!\n\n
            {f"Hope to see you reach {self.BADGE_TIERS.get(next_badge, {}).get('name', 'N/A')}!" if next_badge else "You've reached the highest badge tier!"}
            """,
            from_email="achievements@campusplatz.com",
            recipient_list=[tutor.user.email]
        )
