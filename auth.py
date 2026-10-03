from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import Kullanici, get_db

# Güvenlik ayarları
SECRET_KEY = "savunma-platformu-gizli-anahtar-2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 gün

# Şifre hash'leme
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 şeması
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="giris")

def sifre_hashle(sifre: str) -> str:
    """Şifreyi hash'ler"""
    return pwd_context.hash(sifre)

def sifre_dogrula(duz_sifre: str, hashli_sifre: str) -> bool:
    """Şifreyi doğrular"""
    return pwd_context.verify(duz_sifre, hashli_sifre)

def token_olustur(data: dict) -> str:
    """JWT token oluşturur"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def token_dogrula(token: str) -> dict:
    """JWT token'ı doğrular"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def mevcut_kullanici(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Kullanici:
    """Token'dan mevcut kullanıcıyı alır"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Geçersiz kimlik bilgileri",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = token_dogrula(token)
    if payload is None:
        raise credentials_exception
    
    email = payload.get("sub")
    if email is None:
        raise credentials_exception
    
    kullanici = db.query(Kullanici).filter(Kullanici.email == email).first()
    if kullanici is None:
        raise credentials_exception
    
    return kullanici