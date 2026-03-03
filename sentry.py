import sentry_sdk

sentry_sdk.init(
    dsn="http://a6c87bf3896932238a459148c4d0f87f@192.168.50.177:9000/1", # Replace with your DSN
    traces_sample_rate=1.0, # Capture 100% of traces for performance monitoring
    enable_logs=True,
    attach_stacktrace=True,
    enable_metrics=True,
    environment="dev",
    
    # Other options like enable_logs=True can be added here
)