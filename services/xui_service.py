"""Service for interacting with x-ui panel API."""
import requests
import uuid
import json
import logging
from typing import Optional, Dict, Any
from config import XUI_URL, XUI_USERNAME, XUI_PASSWORD, DEFAULT_PROTOCOL, DEFAULT_TOTAL_GB, DEFAULT_INBOUND_ID, XUI_SUBSCRIPTION_HOST, XUI_SUBSCRIPTION_PORT

# Disable SSL warnings
try:
    from urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    pass

logger = logging.getLogger(__name__)


class XUIService:
    """Service class for x-ui API interactions."""
    
    def __init__(self):
        self.base_url = XUI_URL
        self.username = XUI_USERNAME
        self.password = XUI_PASSWORD
        self.session = requests.Session()
        self._authenticated = False
    
    def _login(self) -> bool:
        """Authenticate with x-ui panel."""
        # Try different login endpoint variations
        login_endpoints = [
            "/login",
            "/xui/login", 
            "/api/login",
            "/login/",
        ]
        
        login_data = {
            "username": self.username,
            "password": self.password
        }
        
        base = self.base_url.rstrip('/')
        
        for endpoint in login_endpoints:
            try:
                login_url = f"{base}{endpoint}"
                logger.info(f"Attempting to login to: {login_url}")
                
                # Try JSON first
                response = self.session.post(login_url, json=login_data, verify=False, timeout=10)
                
                logger.info(f"Login response status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        if result.get("success"):
                            self._authenticated = True
                            logger.info("Successfully authenticated with x-ui panel")
                            return True
                        else:
                            logger.warning(f"Login failed: {result.get('msg', 'Unknown error')}")
                    except ValueError:
                        # Response might not be JSON, try as success if status is 200
                        if response.status_code == 200:
                            self._authenticated = True
                            logger.info("Successfully authenticated with x-ui panel (non-JSON response)")
                            return True
                
                # If 404, try next endpoint
                if response.status_code == 404:
                    logger.debug(f"Endpoint {endpoint} returned 404, trying next...")
                    continue
                
                # Try with form data if JSON didn't work
                if response.status_code != 200:
                    response = self.session.post(login_url, data=login_data, verify=False, timeout=10)
                    if response.status_code == 200:
                        self._authenticated = True
                        logger.info("Successfully authenticated with x-ui panel (form data)")
                        return True
                        
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout connecting to {login_url}")
                continue
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error to {login_url}: {str(e)}")
                return False
            except Exception as e:
                logger.warning(f"Error trying {login_url}: {str(e)}")
                continue
        
        logger.error("Failed to authenticate: all login endpoints returned errors")
        logger.error("Please check:")
        logger.error("1. XUI_URL is correct and accessible")
        logger.error("2. XUI_USERNAME and XUI_PASSWORD are correct")
        logger.error("3. x-ui panel is running and API is enabled")
        return False
    
    def _ensure_authenticated(self) -> bool:
        """Ensure we are authenticated, login if not."""
        if not self._authenticated:
            return self._login()
        return True
    
    def _get_existing_inbound(self, protocol: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get an existing inbound to add clients to.
        Returns the first enabled inbound matching the protocol, or any enabled inbound.
        """
        if not self._ensure_authenticated():
            return None
        
        try:
            base = self.base_url.rstrip('/')
            list_url = f"{base}/panel/api/inbounds/list"
            
            logger.debug(f"Fetching inbounds from: {list_url}")
            response = self.session.get(
                list_url,
                verify=False,
                timeout=10,
                headers={
                    "X-Requested-With": "XMLHttpRequest"
                }
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to list inbounds: {response.status_code}")
                return None
            
            result = response.json()
            inbounds = result.get("obj", [])
            
            if not inbounds:
                logger.warning("No inbounds found")
                return None
            
            # Find first enabled inbound matching protocol
            for inbound in inbounds:
                if inbound.get("enable"):
                    inbound_protocol = inbound.get("protocol", "")
                    if protocol and inbound_protocol == protocol:
                        logger.info(f"Found enabled {protocol} inbound with ID: {inbound.get('id')}")
                        return inbound
                    elif not protocol:
                        logger.info(f"Found enabled inbound with ID: {inbound.get('id')}, protocol: {inbound_protocol}")
                        return inbound
            
            logger.warning("No enabled inbound found")
            return None
            
        except Exception as e:
            logger.error(f"Error getting existing inbound: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_user(self, telegram_user_id: int, username: Optional[str] = None, device_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Create a new user in x-ui panel.
        
        Args:
            telegram_user_id: Telegram user ID
            username: Username from Telegram (required, must be unique for first device)
            device_name: Optional device name (for 2nd+ devices, format: username_device_name)
        
        Returns:
            Dictionary with user info including subscription URL, or None if failed
        """
        if not username:
            logger.error("Username is required for creating user")
            return {
                "success": False,
                "error": "username_required",
                "message": "Имя пользователя не указано. Пожалуйста, установите username в настройках Telegram."
            }
        
        if not self._ensure_authenticated():
            logger.error("Cannot create user: not authenticated")
            return None
        
        try:
            # Determine email format
            if device_name:
                # For additional devices: username_device_name
                email = f"{username}_{device_name}"
                # Check if this specific device already exists
                existing_user = self.find_user_by_username(email)
                if existing_user:
                    # Auto-increment: find next available number
                    counter = 2
                    while True:
                        new_email = f"{username}_{device_name}_{counter}"
                        existing = self.find_user_by_username(new_email)
                        if not existing:
                            email = new_email
                            break
                        counter += 1
                        if counter > 100:  # Safety limit
                            return {
                                "success": False,
                                "error": "too_many_devices",
                                "message": "Слишком много устройств с таким именем. Попробуйте другое имя."
                            }
            else:
                # For first device: just username
                email = username
                # Check if first device already exists
                existing_user = self.find_user_by_username(email)
                if existing_user:
                    logger.warning(f"User with username '{email}' already exists (found during create_user)")
                    return {
                        "success": False,
                        "error": "username_exists",
                        "message": f"Пользователь с именем '{email}' уже существует.",
                        "subscription_url": existing_user.get("subscription_url")
                    }
            # Generate unique UUID for the user
            user_uuid = str(uuid.uuid4())
            
            # Calculate total traffic in bytes (GB to bytes)
            total_traffic = DEFAULT_TOTAL_GB * 1024 * 1024 * 1024
            
            # Find existing inbound to add client to
            inbound_id = None
            
            # If DEFAULT_INBOUND_ID is set, use it
            if DEFAULT_INBOUND_ID is not None:
                inbound_id = DEFAULT_INBOUND_ID
                logger.info(f"Using configured inbound ID: {inbound_id}")
            else:
                # Try to find existing inbound
                existing_inbound = self._get_existing_inbound(DEFAULT_PROTOCOL)
                if existing_inbound:
                    inbound_id = existing_inbound.get("id")
                    logger.info(f"Found existing inbound ID: {inbound_id}")
                else:
                    logger.error(f"No enabled {DEFAULT_PROTOCOL} inbound found and DEFAULT_INBOUND_ID not set.")
                    logger.error("Please either:")
                    logger.error("1. Create an inbound manually in x-ui panel and set DEFAULT_INBOUND_ID in .env")
                    logger.error("2. Or check the correct API endpoint for listing inbounds")
                    return None
            
            # Generate subId for subscription
            import secrets
            sub_id = secrets.token_urlsafe(12)
            
            # Prepare client data according to API format
            # Use email format: username for first device, username_device_name for additional devices
            client_data = {
                "id": user_uuid,
                "flow": "",  # Empty for vless
                "email": email,  # Use format: username or username_device_name
                "limitIp": 0,
                "totalGB": DEFAULT_TOTAL_GB,
                "expiryTime": 0,  # No expiry date
                "enable": True,
                "tgId": str(telegram_user_id),
                "subId": sub_id,
                "comment": "",
                "reset": 0
            }
            
            # For VMESS, add alterId
            if DEFAULT_PROTOCOL == "vmess":
                client_data["alterId"] = 0
            
            # Prepare settings with single client
            client_settings = {
                "clients": [client_data]
            }
            
            # Prepare form data for addClient endpoint
            base = self.base_url.rstrip('/')
            add_client_url = f"{base}/panel/api/inbounds/addClient"
            
            form_data = {
                "id": str(inbound_id),
                "settings": json.dumps(client_settings)
            }
            
            logger.info(f"Adding client via: {add_client_url}")
            logger.debug(f"Form data: {form_data}")
            
            # Send as form data (application/x-www-form-urlencoded)
            response = self.session.post(
                add_client_url,
                data=form_data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest"
                },
                verify=False,
                timeout=10
            )
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response text: {response.text[:500]}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.info(f"Response JSON: {json.dumps(result, indent=2)}")
                    
                    if result.get("success"):
                        # After successful creation, verify user was added by trying to find it
                        # This helps catch cases where user might already exist
                        # Note: We can't easily verify due to API limitations, so we assume success
                        
                        # Get subscription URL using subId
                        subscription_url = self._get_subscription_url(sub_id, inbound_id)
                        
                        logger.info(f"User created successfully. UUID: {user_uuid}, SubId: {sub_id}, Inbound ID: {inbound_id}")
                        
                        return {
                            "success": True,
                            "uuid": user_uuid,
                            "sub_id": sub_id,
                            "inbound_id": inbound_id,
                            "subscription_url": subscription_url,
                            "total_gb": DEFAULT_TOTAL_GB
                        }
                    else:
                        error_msg = result.get("msg", "Unknown error")
                        logger.error(f"API returned success=false: {error_msg}")
                        
                        # Check if error indicates user already exists
                        error_lower = error_msg.lower()
                        if "exist" in error_lower or "duplicate" in error_lower or "already" in error_lower:
                            # Try to find existing user
                            existing_user = self.find_user_by_username(username, inbound_id)
                            if existing_user:
                                return {
                                    "success": False,
                                    "error": "username_exists",
                                    "message": f"Пользователь с именем '{username}' уже существует.",
                                    "subscription_url": existing_user.get("subscription_url")
                                }
                except ValueError as e:
                    logger.error(f"Failed to parse JSON response: {str(e)}")
                    logger.error(f"Response text: {response.text}")
            else:
                logger.error(f"Failed to create user: HTTP {response.status_code}")
                logger.error(f"Response: {response.text[:1000]}")
                
                # Try to parse error message
                try:
                    error_result = response.json()
                    error_msg = error_result.get("msg", "")
                    error_lower = error_msg.lower()
                    if "exist" in error_lower or "duplicate" in error_lower or "already" in error_lower:
                        existing_user = self.find_user_by_username(username, inbound_id)
                        if existing_user:
                            return {
                                "success": False,
                                "error": "username_exists",
                                "message": f"Пользователь с именем '{username}' уже существует.",
                                "subscription_url": existing_user.get("subscription_url")
                            }
                except:
                    pass
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            return None
    
    def _get_subscription_url(self, sub_id: str, inbound_id: Optional[int] = None) -> str:
        """
        Generate subscription URL for the user.
        
        Args:
            sub_id: Subscription ID (subId)
            inbound_id: Optional inbound ID
        
        Returns:
            Subscription URL
        """
        # x-ui subscription URL format: https://server:port/sub/{subId}
        # Subscription URL usually uses different port than panel and doesn't include panel path
        
        if XUI_SUBSCRIPTION_HOST:
            # Use configured subscription host (e.g., "194.87.125.20:2096")
            subscription_url = f"https://{XUI_SUBSCRIPTION_HOST}/sub/{sub_id}"
        elif XUI_SUBSCRIPTION_PORT:
            # Use configured subscription port with host from XUI_URL
            base_url = self.base_url.replace("https://", "").replace("http://", "")
            # Extract host from base URL (remove path and port)
            if ":" in base_url:
                host = base_url.split(":")[0]
            elif "/" in base_url:
                host = base_url.split("/")[0]
            else:
                host = base_url.split(":")[0] if ":" in base_url else base_url
            
            subscription_url = f"https://{host}:{XUI_SUBSCRIPTION_PORT}/sub/{sub_id}"
        else:
            # Fallback: try to extract from XUI_URL but use default subscription port
            base_url = self.base_url.replace("https://", "").replace("http://", "")
            # Extract host from base URL (remove path)
            if "/" in base_url:
                host_port = base_url.split("/")[0]
            else:
                host_port = base_url
            
            # Extract host and use default subscription port (2096)
            if ":" in host_port:
                host = host_port.split(":")[0]
                subscription_url = f"https://{host}:2096/sub/{sub_id}"
            else:
                subscription_url = f"https://{host_port}:2096/sub/{sub_id}"
        
        return subscription_url
    
    def get_inbound_clients(self, inbound_id: int) -> Optional[Dict[str, Any]]:
        """
        Get clients from a specific inbound by fetching all inbounds and finding the one with matching ID.
        
        Args:
            inbound_id: Inbound ID
        
        Returns:
            Inbound data with clients or None if failed
        """
        if not self._ensure_authenticated():
            return None
        
        try:
            base = self.base_url.rstrip('/')
            list_url = f"{base}/panel/api/inbounds/list"
            
            logger.debug(f"Fetching inbounds list to find inbound {inbound_id}")
            response = self.session.get(
                list_url,
                verify=False,
                timeout=10,
                headers={
                    "X-Requested-With": "XMLHttpRequest"
                }
            )
            
            if response.status_code != 200:
                logger.warning(f"Failed to list inbounds: {response.status_code}")
                return None
            
            result = response.json()
            inbounds = result.get("obj", [])
            
            # Find inbound with matching ID
            for inbound in inbounds:
                if inbound.get("id") == inbound_id:
                    logger.info(f"Successfully found inbound {inbound_id}")
                    return inbound
            
            logger.warning(f"Inbound {inbound_id} not found in list")
            return None
            
        except Exception as e:
            logger.error(f"Error getting inbound clients: {str(e)}")
            return None
    
    def find_user_by_username(self, username: str, inbound_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Find user by username/email in inbound.
        
        Args:
            username: Username/email to search for
            inbound_id: Optional inbound ID (if None, uses DEFAULT_INBOUND_ID)
        
        Returns:
            Dictionary with user info and subscription URL, or None if not found
        """
        if not self._ensure_authenticated():
            return None
        
        try:
            # Use provided inbound_id or default
            check_inbound_id = inbound_id if inbound_id is not None else DEFAULT_INBOUND_ID
            
            if not check_inbound_id:
                logger.warning("No inbound ID available for user lookup")
                return None
            
            # Get inbound with clients
            inbound = self.get_inbound_clients(check_inbound_id)
            if not inbound:
                # If we can't get inbound data, we can't check for existing users
                # This is OK - we'll rely on API error handling during creation
                logger.warning(f"Cannot get inbound {check_inbound_id} data - skipping username check")
                return None
            
            # Parse settings
            settings = inbound.get("settings", {})
            if isinstance(settings, str):
                try:
                    settings = json.loads(settings)
                except json.JSONDecodeError:
                    logger.error("Failed to parse settings JSON")
                    return None
            
            # Search for user by email/username
            clients = settings.get("clients", [])
            for client in clients:
                client_email = client.get("email", "")
                if client_email == username:
                    # Found user!
                    sub_id = client.get("subId", "")
                    if sub_id:
                        subscription_url = self._get_subscription_url(sub_id, check_inbound_id)
                        return {
                            "found": True,
                            "username": username,
                            "sub_id": sub_id,
                            "uuid": client.get("id"),
                            "subscription_url": subscription_url,
                            "inbound_id": check_inbound_id
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding user by username: {str(e)}")
            return None
    
    def get_user_subscription(self, telegram_user_id: int, username: Optional[str] = None) -> Optional[str]:
        """
        Get subscription URL for existing user by Telegram ID or username.
        Returns first subscription found (for backward compatibility).
        
        Args:
            telegram_user_id: Telegram user ID
            username: Optional username to search for
        
        Returns:
            Subscription URL or None if user not found
        """
        all_subscriptions = self.get_all_user_subscriptions(telegram_user_id, username)
        if all_subscriptions:
            return all_subscriptions[0].get("subscription_url")
        return None
    
    def get_all_user_subscriptions(self, telegram_user_id: int, username: Optional[str] = None) -> list[Dict[str, Any]]:
        """
        Get all subscription URLs for user by Telegram ID.
        
        Args:
            telegram_user_id: Telegram user ID
            username: Optional base username (for finding first device)
        
        Returns:
            List of dictionaries with subscription info: [{"email": "...", "subscription_url": "...", "device_name": "..."}, ...]
        """
        if not self._ensure_authenticated():
            return []
        
        subscriptions = []
        
        try:
            if not DEFAULT_INBOUND_ID:
                logger.warning("No inbound ID available for subscription lookup")
                return []
            
            inbound = self.get_inbound_clients(DEFAULT_INBOUND_ID)
            if not inbound:
                return []
            
            settings = inbound.get("settings", {})
            if isinstance(settings, str):
                try:
                    settings = json.loads(settings)
                except json.JSONDecodeError:
                    return []
            
            clients = settings.get("clients", [])
            base_username = username if username else None
            
            for client in clients:
                client_tg_id = client.get("tgId", "")
                client_email = client.get("email", "")
                
                # Check if this client belongs to the user
                # PRIMARY check: Match by Telegram ID (this is the main identifier)
                if client_tg_id != str(telegram_user_id):
                    continue  # Skip clients that don't belong to this user
                
                # If we reach here, the client belongs to the user (by telegram_id)
                sub_id = client.get("subId", "")
                if not sub_id:
                    continue  # Skip clients without sub_id
                
                subscription_url = self._get_subscription_url(sub_id, DEFAULT_INBOUND_ID)
                
                # Extract device name from email
                # Use base_username to determine if this is first device or additional device
                device_name = None
                if base_username:
                    if client_email == base_username:
                        device_name = "Основное устройство"  # First device
                    elif client_email.startswith(base_username + "_"):
                        # Additional device: extract name after username_
                        device_name = client_email[len(base_username) + 1:]
                    else:
                        # Email doesn't match expected pattern, use email as fallback
                        device_name = client_email
                else:
                    # No base_username provided, use email as device name
                    device_name = client_email
                
                subscriptions.append({
                    "email": client_email,
                    "subscription_url": subscription_url,
                    "device_name": device_name or client_email,
                    "sub_id": sub_id
                })
            
            return subscriptions
            
        except Exception as e:
            logger.error(f"Error getting all user subscriptions: {str(e)}")
            return []

