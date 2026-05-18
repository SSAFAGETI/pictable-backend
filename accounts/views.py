from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
import requests

from .models import OauthAccount
from .serializers import SignupSerializer, LoginSerializer, LogoutSerializer

User = get_user_model()

# Create your views here.
@api_view(['POST'])
def signup(request):
    serializer = SignupSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response(
            {
                'message': '회원가입이 완료되었습니다.',
                'email': user.email,
                'nickname': user.nickname,
            },
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def login(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'message': '로그인 성공',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'email': user.email,
                'nickname': user.nickname,
            },
            status=status.HTTP_200_OK
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def logout(request):
    serializer = LogoutSerializer(data=request.data)
    if serializer.is_valid():
        return Response(
            {'message': '로그아웃 되었습니다.'},
            status=status.HTTP_200_OK
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def google_login(request):
    code = request.data.get('code')
    redirect_uri = redirect_uri = settings.GOOGLE_REDIRECT_URI
    
    if not code:
        return Response({'error': 'code가 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

    # 1. code로 구글에 access_token 요청
    token_response = requests.post(
        'https://oauth2.googleapis.com/token',
        data={
            'code' : code,
            'client_id' : settings.GOOGLE_CLIENT_ID,
            'client_secret' : settings.GOOGLE_CLIENT_SECRET,
            'redirect_uri' : redirect_uri,
            'grant_type' : 'authorization_code',
        }
    )
    token_data = token_response.json()

    if 'error' in token_data:
        return Response({'error': '구글 토큰 요청 실패', 'detail': token_data}, status=status.HTTP_400_BAD_REQUEST)

    # 2. access_token으로 구글 유저 정보 가져오기
    user_info_response = requests.get(
        'https://www.googleapis.com/oauth2/v2/userinfo',
        headers={'Authorization': f'Bearer {token_data["access_token"]}'}
    )
    user_info = user_info_response.json()

    email = user_info.get('email')
    name  = user_info.get('name')
    provider_user_id = user_info.get('id')

    if not email:
        return Response({'error': '이메일 정보를 가져올 수 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

    # 3. 유저 있으면 로그인, 없으면 생성
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'nickname' : name or email.split('@')[0],
            'provider' : 'google',
        }
    )

    # 4. OauthAccount 저장
    OauthAccount.objects.get_or_create(
        user=user,
        provider='google',
        defaults={'provider_user_id': provider_user_id}
    )

    # 5. JWT 발급
    refresh = RefreshToken.for_user(user)
    return Response({
        'access' : str(refresh.access_token),
        'refresh' : str(refresh),
        'created' : created,
    })