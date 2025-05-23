from django.db import models
from users.models import User,Tutor
from datetime import timedelta
import uuid
from payments.models import PaymentForLiveClass
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from encrypted_model_fields.fields import EncryptedCharField
import base64
from django.conf import settings
from django.utils import timezone
from simple_history.models import HistoricalRecords
import hashlib
from django.utils.timezone import now


def generate_uid_for_live_class():
    return generate_short_uid(
        model_class=LiveClassSession,
        field_name="uid",
        session_date=now().date(),  # or None to use default logic
        suffix_length=6
    )

def generate_short_uid(model_class, field_name="uid", session_date=None, suffix_length=6):
    date_str = session_date.strftime('%Y-%m-%d') if session_date else now().date().strftime('%Y-%m-%d')
    while True:
        short_hash = hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:suffix_length]
        uid = f"{date_str}-{short_hash}"
        if not model_class.objects.filter(**{field_name: uid}).exists():
            return uid


class TutorLiveClassApiSettings(models.Model):
    class KeySource(models.TextChoices):
        PLATFORM = 'PLATFORM', 'Platform Default'
        CUSTOM = 'CUSTOM', 'Custom Keys'

    tutor = models.OneToOneField(Tutor, on_delete=models.CASCADE, related_name='video_settings' )
    
    # Key Configuration
    key_source = models.CharField(max_length=22,choices=KeySource.choices,default=KeySource.PLATFORM,help_text="Source of API keys for this tutor")
    custom_livekit_key = EncryptedCharField(max_length=256,blank=True,help_text="Encrypted LiveKit API key (leave blank for platform default)")
    custom_daily_co_key = EncryptedCharField(max_length=256,blank=True,help_text="Encrypted Daily.co API key (leave blank for platform default)")
    
    # Compliance Flags
    gdpr_consent = models.BooleanField(default=False,help_text="Tutor consents to data processing under GDPR")
    coc_agreement = models.DateTimeField(null=True, blank=True, help_text="Timestamp of Code of Conduct acceptance")
    
    # Network Verification
    bandwidth_verified = models.BooleanField( default=False, help_text="Tutor meets minimum bandwidth requirements" )
    last_bandwidth_test = models.DateTimeField( null=True, blank=True, help_text="Last network test timestamp")
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = "Tutor Video Settings"
        verbose_name_plural = "Tutor Video Settings"

    def get_livekit_key(self):
        return self.custom_livekit_key if self.key_source == self.KeySource.CUSTOM else settings.LIVEKIT_API_KEY

    def get_daily_co_key(self):
        return self.custom_daily_co_key if self.key_source == self.KeySource.CUSTOM else settings.DAILY_MASTER_KEY



class LiveClassSession(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', 'Scheduled'
        ONGOING = 'ONGOING', 'Ongoing'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        CANCELLED = 'CANCELED', 'Canceled'

    class Provider(models.TextChoices):
        LIVEKIT = 'LIVEKIT', 'LiveKit'
        DAILY_CO = 'DAILY_CO', 'Daily.co'
        FALLBACK = 'FALLBACK', 'Browser WebRTC'

    # Core Identifiers
    uid = models.CharField(max_length=16,default=generate_uid_for_live_class,editable=False,unique=True,help_text="Public session identifier for GDPR-safe sharing")
    tutor = models.ForeignKey(Tutor,on_delete=models.SET_NULL, null=True, related_name='live_classes')
    learner = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,related_name='live_classes')
    payment = models.ForeignKey(PaymentForLiveClass,on_delete=models.SET_NULL,null=True,related_name='live_class')
    status = models.CharField(max_length=10,choices=Status.choices,default=Status.FAILED)
   

    livekit_room_name = models.CharField(max_length=100, blank=True,null=True)
    livekit_tutor_token = models.TextField(blank=True,null=True)  # JWT can be long
    livekit_learner_token = models.TextField(blank=True,null=True)
    livekit_tutor_url = models.TextField(blank=True,null=True)  
    livekit_learner_url = models.TextField(blank=True,null=True)
    
    
    daily_co_room_name = models.CharField(max_length=100, blank=True)
    daily_co_tutor_token = models.TextField(blank=True,null=True)  
    daily_co_learner_token = models.TextField(blank=True,null=True)
    daily_co_room_url = models.URLField(blank=True)
    daily_co_tutor_url = models.URLField(blank=True)
    daily_co_learner_url = models.URLField(blank=True)
    daily_co_room_id = models.CharField(max_length=50, blank=True)
    
    date = models.DateField(null=True, blank=True, db_index=True) 
    scheduled_start_time = models.DateTimeField(db_index=True,help_text="Scheduled start in tutor's timezone" )
    actual_start_time = models.DateTimeField(null=True, blank=True, db_index=True )
    end_time = models.DateTimeField(db_index=True)

    primary_provider = models.CharField(max_length=10,choices=Provider.choices,default=Provider.LIVEKIT)
    actual_provider = models.CharField( max_length=10, choices=Provider.choices, null=True, blank=True)

    is_fallback_triggered = models.BooleanField(default=False)
    
    # Legal Compliance
    recording_consent = models.BooleanField(default=False,help_text="Learner consented to recording (GDPR Article 7)")
    
    created_at = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()

    class Meta:
        indexes = [
            models.Index(fields=['tutor', 'scheduled_start_time']),
            models.Index(fields=['learner', 'scheduled_start_time']),
            models.Index(fields=['uid', 'scheduled_start_time']),
        ]
        ordering = ['-scheduled_start_time']

    def save(self, *args, **kwargs):
        if not self.actual_provider:
            self.actual_provider = self.primary_provider

        if not self.uid:
            self.uid = generate_short_uid(model_class=LiveClassSession,session_date=self.date)

        super().save(*args, **kwargs)


class LiveKitClassJoinURL(models.Model):
    key = models.CharField(max_length=16, unique=True)
    session = models.ForeignKey(LiveClassSession, on_delete=models.CASCADE)
    role = models.CharField(max_length=10)  
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    history = HistoricalRecords()


class FallbackEvent(models.Model):
    session = models.ForeignKey(LiveClassSession, on_delete=models.CASCADE)
    triggered_by = models.CharField(max_length=20, choices=[('AUTO', 'System'),('MANUAL', 'Tutor')])
    reason = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()


class SessionTelemetry(models.Model):

    session = models.ForeignKey(LiveClassSession,on_delete=models.CASCADE,related_name='telemetry')
    timestamp = models.DateTimeField( auto_now_add=True,db_index=True)
    
    # Network QoS
    packet_loss = models.FloatField( validators=[MinValueValidator(0.0), MaxValueValidator(1.0)], help_text="Packet loss ratio (0.05 = 5%)")
    latency_ms = models.FloatField( validators=[MinValueValidator(0)], help_text="Round-trip latency in milliseconds")
    jitter_ms = models.FloatField( validators=[MinValueValidator(0)], help_text="Network jitter in milliseconds")
    
    resolution = models.CharField(max_length=9,
        choices=[
            ('240p', '426x240'),
            ('360p', '640x360'),
            ('480p', '854x480'),
            ('720p', '1280x720')
        ],
        help_text="Current output resolution"
    )
    fps = models.PositiveSmallIntegerField(validators=[MaxValueValidator(60)],help_text="Frames per second")
   
    provider = models.CharField(max_length=10,choices=LiveClassSession.Provider.choices)
    is_fallback = models.BooleanField( default=False)
    
    created_at = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = "Session Telemetry"
        get_latest_by = 'timestamp'


class SessionRecording(models.Model):
    session = models.ForeignKey( LiveClassSession, on_delete=models.CASCADE, related_name='recording')
    title = models.CharField(max_length=64, blank=True)
    
    storage_id = models.CharField( max_length=256, unique=True, help_text="Opaque storage identifier (GDPR pseudonymization)")
    storage_region = models.CharField( max_length=20,default='eu-west-1', help_text="AWS/GCP region for data residency compliance")
    encryption_key_id = models.CharField( max_length=64,help_text="KMS key identifier for encrypted storage")
    
    # Content Metadata
    duration_seconds = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    file_size_mb = models.DecimalField(max_digits=6,decimal_places=2,validators=[MinValueValidator(0.01)])
    
    retention_days = models.PositiveSmallIntegerField(default=30,validators=[MaxValueValidator(365)],help_text="Days before automatic deletion (GDPR Right to Erasure)")
    
    # LiveKit References
    egress_id = models.CharField(max_length=64,blank=True,help_text="LiveKit's egress job ID")
    livekit_mp4_url = models.URLField( blank=True, help_text="Temporary LiveKit MP4 URL (expires in 24h)" )
    
    download_attempts = models.PositiveSmallIntegerField(default=0, help_text="Number of download retries" )
    
    # Status Tracking
    RECORDING_STATUS = [
        ('STARTED', 'Recording Started'),
        ('COMPLETED', 'Recording Completed'),
        ('FAILED', 'Recording Failed')
    ]
    status = models.CharField(max_length=12,choices=RECORDING_STATUS,default='REQUESTED' )
    created_at = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Session Recording"
        verbose_name_plural = "Session Recordings"

    def __str__(self):
        return f"Recording for {self.session.uid}"



class SessionEventLog(models.Model):
    class EventType(models.TextChoices):
        PARTICIPANT_JOINED = 'participant_joined', 'Participant Joined'
        PARTICIPANT_LEFT = 'participant_left', 'Participant Left'
        TRACK_PUBLISHED = 'track_published', 'Track Published'
        TRACK_UNPUBLISHED = 'track_unpublished', 'Track Unpublished'
        RECORDING_STARTED = 'recording_started', 'Recording Started'
        RECORDING_ENDED = 'recording_ended', 'Recording Ended'
        ROOM_STARTED = 'room_started', 'Room started'
        ROOM_FINISHED = 'room_finished', 'Room finished'
        INGRESS_STARTED = 'ingress_started', 'Ingress Started'
        INGRESS_ENDED = 'ingress_ended', 'Ingress Ended'

    session = models.ForeignKey('LiveClassSession', on_delete=models.CASCADE)
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    participant_sid = models.CharField(max_length=64, blank=True)
    participant_identity = models.CharField(max_length=255, blank=True)
    participant_role = models.CharField(max_length=10, blank=True)  # 'tutor' or 'learner'
    metadata = models.JSONField(default=dict)  # Additional event data
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        indexes = [
            models.Index(fields=['session', 'event_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.session.id} -{self.event_type} - {self.participant_identity}"




'''
Add to RecordedSession :

 # Storage Details
    STORAGE_PROVIDERS = [
        ("S3", "Amazon S3"),
        ("GCS", "Google Cloud Storage"),
        ("AZURE", "Azure Blob"),
    ]
    storage_provider = models.CharField(
        max_length=10,
        choices=STORAGE_PROVIDERS,
        default="S3"
    )
    storage_path = models.CharField(
        max_length=255,
        help_text="Path in bucket (e.g. recordings/2023/session123.mp4)"
    )
    file_size_mb = models.PositiveIntegerField(
        null=True,
        help_text="File size in megabytes"
    )
    
    # Access Control
    is_public = models.BooleanField(
        default=False,
        help_text="Can non-participants view?"
    )
    encryption_key = models.CharField(
        max_length=100,
        blank=True,
        help_text="KMS key ID for encrypted recordings"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)



class SessionQoS(models.Model):
    session = models.OneToOneField(
        LiveClassSession,
        on_delete=models.CASCADE,
        related_name='qos_data'
    )
    connection_quality_log = JSONField(
        default=list,
        help_text="Timestamps with quality metrics"
    )
    average_bitrate = models.FloatField(
        null=True,
        help_text="kbps average during session"
    )
    reconnects_count = models.PositiveIntegerField(default=0)
    network_switches = JSONField(
        default=list,
        help_text="Agora->Daily.co fallback events"
    )

# 2. Device/Network Metadata
class SessionDevices(models.Model):
    session = models.ForeignKey(
        LiveClassSession,
        on_delete=models.CASCADE,
        related_name='device_info'
    )
    user = models.ForeignKey(  # Tutor or Student
        User,
        on_delete=models.CASCADE
    )
    os = models.CharField(max_length=50)
    browser = models.CharField(max_length=50)
    resolution = models.CharField(max_length=20)  # "1280x720"
    network_type = models.CharField(  # "wifi", "4g", "ethernet"
        max_length=20,
        blank=True
    )

# 3. Recording Analytics
class RecordingAnalytics(models.Model):
    recording = models.OneToOneField(
        RecordedSession,
        on_delete=models.CASCADE,
        related_name='analytics'
    )
    playback_stats = JSONField(
        default=list,
        help_text="Per-viewer watch metrics"
    )
    storage_provider = models.CharField(
        max_length=20,
        choices=[("S3", "S3"), ("GCS", "Google Cloud"), ("AZURE", "Azure")]
    )
    encryption_key_id = models.CharField(
        max_length=100,
        blank=True
    )

# 4. Tutor Streaming Preferences
class TutorStreamSettings(models.Model):
    tutor = models.OneToOneField(
        TutorProfile,
        on_delete=models.CASCADE,
        related_name='stream_prefs'
    )
    max_bitrate_kbps = models.PositiveIntegerField(
        default=2500,
        validators=[MinValueValidator(500)]
    )
    preferred_resolution = models.CharField(
        max_length=10,
        choices=[("SD", "640x480"), ("HD", "1280x720"), ("FHD", "1920x1080")]
    )
    banned_countries = JSONField(default=list)  # ["IR", "CU"] 

    '''