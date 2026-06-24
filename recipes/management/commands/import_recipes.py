import re
import requests
import xml.etree.ElementTree as ET
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from recipes.models import Recipe, RecipeStep, RecipeIngredient, Tag, RecipeImage
from medias.models import MediaFile

User = get_user_model()


class Command(BaseCommand):
    help = '식품안전처 API에서 레시피 데이터를 가져옵니다.'

    def add_arguments(self, parser):
        parser.add_argument('--start', type=int, default=1)
        parser.add_argument('--end',   type=int, default=100)

    def split_ingredients(self, text):
        result  = []
        depth   = 0
        current = ''
        for char in text:
            if char == '(':
                depth += 1
                current += char
            elif char == ')':
                depth -= 1
                current += char
            elif char in (',', '\n') and depth == 0:
                if current.strip():
                    result.append(current.strip())
                current = ''
            else:
                current += char
        if current.strip():
            result.append(current.strip())
        return result

    def parse_ingredient(self, text):
        text = text.strip()
        if not text:
            return None, None

        paren_contents = re.findall(r'\(([^)]+)\)', text)
        name = re.sub(r'\([^)]+\)', '', text).strip()

        amount = ''

        if paren_contents:
            for paren in paren_contents:
                if re.search(r'\d', paren):
                    amount_match = re.search(r'[\d./]+\s*[a-zA-Z가-힣]+', paren)
                    if amount_match:
                        amount = amount_match.group().strip()
                    break
            name = re.sub(r'\s*[\d./]+\s*[a-zA-Zㄱ-힣]+$', '', name).strip()
        else:
            match = re.match(
                r'^(.+?)\s+([\d./]+\s*(?:ml|l|g|kg|cc|개|큰술|작은술|컵|봉지|장|줄기|마리|모|쪽|알|팩|캔|병|통|cm|mm))$',
                text, re.IGNORECASE
            )
            if match:
                name   = match.group(1).strip()
                amount = match.group(2).strip()
            else:
                name   = text
                amount = ''

        return name or None, amount

    def clean_url(self, url):
        if not url:
            return ''
        return url.strip()

    def handle(self, *args, **options):
        start = options['start']
        end   = options['end']

        url = f'http://openapi.foodsafetykorea.go.kr/api/{settings.FOOD_API_KEY}/COOKRCP01/xml/{start}/{end}'
        self.stdout.write(f'API 호출 중... {url}')

        response = requests.get(url)
        root     = ET.fromstring(response.content)

        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            self.stdout.write(self.style.ERROR('슈퍼유저가 없습니다.'))
            return

        count = 0
        for row in root.findall('.//row'):
            title         = row.findtext('RCP_NM', '').strip()
            parts         = row.findtext('RCP_PARTS_DTLS', '').strip()
            category      = row.findtext('RCP_PAT2', '').strip()
            thumbnail_url = self.clean_url(row.findtext('ATT_FILE_NO_MAIN', '').strip())
            mk_url        = self.clean_url(row.findtext('ATT_FILE_NO_MK', '').strip())

            if not title:
                continue

            if Recipe.objects.filter(title=title, source_type='api').exists():
                continue

            # 썸네일 MediaFile 생성
            thumbnail_media = None
            if thumbnail_url:
                thumbnail_media = MediaFile.objects.create(
                    uploader_user = admin,
                    url           = thumbnail_url,
                    mime_type     = 'image/png',
                    purpose       = 'thumbnail',
                )

            recipe = Recipe.objects.create(
                author          = admin,
                title           = title,
                description     = parts,
                servings        = 2,
                cook_time       = 30,
                source_type     = 'api',
                is_public       = True,
                thumbnail_media = thumbnail_media,
            )

            # MK 이미지 RecipeImage로 저장
            if mk_url:
                mk_media = MediaFile.objects.create(
                    uploader_user = admin,
                    url           = mk_url,
                    mime_type     = 'image/png',
                    purpose       = 'recipe_image',
                )
                RecipeImage.objects.create(
                    recipe     = recipe,
                    media_file = mk_media,
                    sort_order = 0,
                )

            # 재료 파싱
            parts_clean = parts
            if parts_clean.startswith('재료'):
                parts_clean = parts_clean[2:].strip()

            raw_ingredients = self.split_ingredients(parts_clean)

            for ingredient in raw_ingredients:
                ingredient = ingredient.strip()

                if ':' in ingredient:
                    ingredient = ingredient.split(':')[1].strip()

                name, amount = self.parse_ingredient(ingredient)

                if name:
                    RecipeIngredient.objects.create(
                        recipe = recipe,
                        name   = name,
                        amount = amount or '',
                    )

            # 태그 처리
            if category:
                tag, _ = Tag.objects.get_or_create(name=category)
                recipe.tags.add(tag)

            # 조리 스텝 파싱
            for i in range(1, 21):
                step_text    = row.findtext(f'MANUAL{i:02d}', '').strip()
                step_img_url = self.clean_url(row.findtext(f'MANUAL_IMG{i:02d}', '').strip())

                if step_text:
                    step_media = None
                    if step_img_url:
                        step_media = MediaFile.objects.create(
                            uploader_user = admin,
                            url           = step_img_url,
                            mime_type     = 'image/png',
                            purpose       = 'step',
                        )

                    RecipeStep.objects.create(
                        recipe      = recipe,
                        order       = i,
                        description = step_text,
                        image       = step_media,
                    )

            count += 1
            self.stdout.write(f'저장 완료 : {title}')

        self.stdout.write(self.style.SUCCESS(f'총 {count}개 레시피 저장 완료'))