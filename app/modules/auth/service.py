"""
Auth service — business logic layer.

Contains authentication business logic for login, register, and logout.
Delegates data access to the repository layer.
Must be independent of web framework (per backend development rules).
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.modules.auth.dto import (
    LoginRequestDTO,
    LoginResponseDTO,
    LogoutResponseDTO,
    RegisterRequestDTO,
    RegisterResponseDTO,
    UserResponseDTO,
    VerifyEmailResponseDTO
)
from app.modules.auth.exceptions import (
    EmailAlreadyExistsException,
    InvalidCredentialsException,
    InvalidIncomeTypeException,
)
from app.modules.auth.repository import AuthRepository
from app.modules.transactions.entities import Transaction
from app.modules.transactions.repository import TransactionsRepository
from app.modules.users.entities import User
from app.shared.security.jwt_handler import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.shared.security.password import hash_password, verify_password
from app.shared.security.token_blacklist import token_blacklist

SANTIAGO_TZ = ZoneInfo("America/Santiago")


class AuthService:
    """Business logic for authentication operations."""

    def __init__(self, repository: AuthRepository, transactions_repository: TransactionsRepository):
        self._repository = repository
        self._transactions_repository = transactions_repository

    def login(self, dto: LoginRequestDTO) -> LoginResponseDTO:
        """Authenticate a user and generate JWT tokens.

        Args:
            dto: Login request with email and password.

        Returns:
            Login response with access/refresh tokens and user data.

        Raises:
            InvalidCredentialsException: If email not found or password wrong.
        """
        user = self._repository.get_user_by_email(dto.email)
        if not user or not verify_password(dto.password, user.password):
            raise InvalidCredentialsException()

        access_token, _, expires_in = create_access_token(
            str(user.user_id), user.email, user.first_name, user.last_name
        )
        refresh_token, _ = create_refresh_token(str(user.user_id))

        return LoginResponseDTO(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=expires_in,
            message="Inicio de sesión exitoso",
            user=UserResponseDTO(
                id=user.user_id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                created_at=user.created_at,
            ),
        )

    def register(self, dto: RegisterRequestDTO) -> RegisterResponseDTO:
        """Register a new user account.

        Validates business rules, creates the user, and links interest topics.

        Args:
            dto: Registration request with user details and topics.

        Returns:
            Registration response with user confirmation.

        Raises:
            EmailAlreadyExistsException: If email is already registered.
            InvalidIncomeTypeException: If income type doesn't exist.
        """
        # Check email uniqueness
        existing = self._repository.get_user_by_email(dto.email)
        if existing:
            raise EmailAlreadyExistsException()

        # Validate income type exists in database
        income_type = self._repository.get_income_type_by_id(dto.income_type)
        if not income_type:
            raise InvalidIncomeTypeException()

        # Create user with hashed password
        user = User(
            first_name=dto.first_name,
            last_name=dto.last_name,
            email=dto.email,
            password=hash_password(dto.password),
            birth_date=dto.birth_date,
            income_type_id=income_type.income_type_id,
            monthly_income=dto.monthly_income,
            monthly_expenses=dto.monthly_expenses,
        )
        created_user = self._repository.create_user(user)

        # Create user interests (news tags)
        tags = self._repository.get_news_tags_by_ids(dto.topics)
        if tags:
            tag_ids = [tag.tag_id for tag in tags]
            self._repository.create_user_interests(
                created_user.user_id, tag_ids
            )

        # Create default transactions (income: Sueldo, expense: Otros Gastos)
        now = datetime.now(SANTIAGO_TZ).replace(microsecond=0)

        income_type = self._transactions_repository.get_transaction_type_by_name("Ingreso")
        expense_type = self._transactions_repository.get_transaction_type_by_name("Gasto")
        sueldo_category = self._transactions_repository.get_transaction_category_by_name("Sueldo")
        otros_gastos_category = self._transactions_repository.get_transaction_category_by_name("Otros Gastos")
        monthly_frequency = self._transactions_repository.get_transaction_frequency_by_name("Mensual")

        # Income transaction (Sueldo)
        income_tx = Transaction(
            user_id=created_user.user_id,
            amount=dto.monthly_income,
            transaction_type_id=income_type.transaction_type_id,
            transaction_category_id=sueldo_category.transaction_category_id,
            transaction_frequency_id=monthly_frequency.transaction_frequency_id,
            description=None,
            transaction_date=now,
        )
        self._transactions_repository.add_transaction(income_tx)

        # Expense transaction (Otros Gastos)
        expense_tx = Transaction(
            user_id=created_user.user_id,
            amount=dto.monthly_expenses,
            transaction_type_id=expense_type.transaction_type_id,
            transaction_category_id=otros_gastos_category.transaction_category_id,
            transaction_frequency_id=monthly_frequency.transaction_frequency_id,
            description="Gasto estimado del usuario",
            transaction_date=now,
        )
        self._transactions_repository.add_transaction(expense_tx)

        return RegisterResponseDTO(
            message="Usuario creado correctamente",
            user=UserResponseDTO(
                id=created_user.user_id,
                first_name=created_user.first_name,
                last_name=created_user.last_name,
                email=created_user.email,
                created_at=created_user.created_at,
            )
        )

    def logout(self, token: str) -> LogoutResponseDTO:
        """Invalidate a JWT token by blacklisting its JTI.

        Args:
            token: The JWT access token to invalidate.

        Returns:
            Logout confirmation response.

        Raises:
            ValueError: If the token is invalid or expired.
        """
        payload = decode_token(token)
        jti = payload.get("jti")
        exp_timestamp = payload.get("exp")

        if jti and exp_timestamp:
            exp = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            token_blacklist.blacklist_token(jti, exp)

        return LogoutResponseDTO(message="Cierre de sesión exitoso")

    def verify_email(self, email: str) -> VerifyEmailResponseDTO:
        """Check if an email already exists in the database.

        Args:
            email: The email address to verify.

        Returns:
            Response indicating if the email exists and a descriptive message.
        """
        user = self._repository.get_user_by_email(email)
        exists = user is not None
        message = (
            "El correo ya se encuentra registrado"
            if exists
            else "El correo está disponible"
        )
        return VerifyEmailResponseDTO(exists=exists, message=message)
