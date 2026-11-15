"""fde-backend-service: a multi-user backend service built with FastAPI.

Domain: a community clinic appointment and referral queue (synthetic data
only). The service demonstrates registration and login with hashed
passwords, JWT access and refresh tokens, role-based authorization,
full CRUD, signed outbound webhooks with retry and a delivery log, and
a third-party API integration (Open-Meteo weather, no key required).
"""

__version__ = "1.0.0"
