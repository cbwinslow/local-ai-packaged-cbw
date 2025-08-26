from fastapi import FastAPI, Depends
from auth import require_user

app = FastAPI(title='OpenDiscourse API', version='0.1.0')

@app.get('/healthz')
def healthz():
    return {'ok': True}

@app.get('/v1/secure/ping')
def ping(user=Depends(require_user)):
    return {'ok': True, 'sub': user.get('sub'), 'role': user.get('role')}
