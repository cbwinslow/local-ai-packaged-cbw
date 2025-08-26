#!/usr/bin/env python3
import os, time, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

ALGO = 'HS256'
JWT_SECRET = os.getenv('SUPABASE_JWT_SECRET','')
if not JWT_SECRET:
    raise RuntimeError('SUPABASE_JWT_SECRET not set')
bearer = HTTPBearer(auto_error=False)

def _decode(tok:str)->dict:
    try:
        p = jwt.decode(tok, JWT_SECRET, algorithms=[ALGO])
        if 'exp' in p and int(time.time()) >= int(p['exp']):
            raise HTTPException(status_code=401, detail='Token expired')
        return p
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f'JWT error: {e}')

def require_user(creds:HTTPAuthorizationCredentials|None=Depends(bearer)):
    if creds is None or not creds.credentials or '.' not in creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing token')
    return _decode(creds.credentials)
