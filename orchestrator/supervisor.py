from db_utils import log_metric

class Supervisor:
    def monitor(self, assistant_type, latency, error_rate, user_id):
        log_metric(assistant_type, latency, error_rate, user_id)
        # Add more supervision logic if needed, e.g., alerts