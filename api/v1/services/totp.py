from api.core.base.services import Service
from sqlalchemy.orm import Session
from api.v1.schemas.totp_device import TOTPDeviceRequestSchema
from fastapi import HTTPException, status
from api.v1.models import TOTPDevice
import pyotp
import qrcode
import io
import base64
from sqlalchemy.exc import SQLAlchemyError


class TOTPService(Service):
    """
    Service class providing TOTP functionality for two-factor authentication.

    This service class handles all operations related to TOTP devices, including creating TOTP devices,
    generating secrets, otpauth URLs, QR codes, and verifying OTP tokens.
    """

    def create(self, db: Session, schema: TOTPDeviceRequestSchema) -> TOTPDevice:
        """Create a new TOTP device"""
        try:
            if self.fetch(db=db, user_id=schema.user_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="totp device for this user already exists",
                )
            totp_device = TOTPDevice(**schema.model_dump())
            db.add(totp_device)
            db.commit()
            db.refresh(totp_device)
            return totp_device
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}",
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating TOTP device: {str(e)}",
            )

    def fetch(self, db: Session, user_id: str) -> TOTPDevice | None:
        """Fetch a TOTP device by corresponding user id"""

        try:
            return db.query(TOTPDevice).filter(TOTPDevice.user_id == user_id).first()
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error when fetching TOTP device: {str(e)}",
            )
            
    def fetch_all(self):
        pass

    def update(self):
        pass

    def delete(self):
        pass

    def generate_secret(self) -> str:
        """Generate a unique secret for the TOTP device"""

        try:
            return pyotp.random_base32()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating TOTP secret: {str(e)}",
            )

    def generate_otpauth_url(self, secret: str, user_email: str, app_name: str) -> str:
        """Generate otpauth URL for the authenticator app"""

        try:
            totp = pyotp.TOTP(secret)
            return totp.provisioning_uri(name=user_email, issuer_name=app_name)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating otpauth URL: {str(e)}",
            )

    def generate_qrcode(self, otpauth_url: str) -> str:
        """Generate a QR code for the otpauth URL and returns it as base64 string"""

        try:
            qr = qrcode.make(otpauth_url)
            buffer = io.BytesIO()
            qr.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode("utf-8")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating QR code: {str(e)}",
            )


totp_service = TOTPService()
