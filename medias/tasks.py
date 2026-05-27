# tasks.py - 단순하게
from .services.gemini_service import analyze_ingredients
from .models import IngredientDetectionJob, IngredientDetectionItem, IngredientCatalog
from django.utils import timezone

def run_ingredient_detection(job_id: int, file_obj) -> None:
    job = IngredientDetectionJob.objects.get(id=job_id)

    try:
        job.status = 'processing'
        job.save(update_fields=['status'])

        result = analyze_ingredients(file_obj)

        for item in result.get("items", []):
            catalog_obj = IngredientCatalog.objects.filter(name=item["name"]).first()
            IngredientDetectionItem.objects.create(
                detection_job = job,
                ingredient    = catalog_obj,
                detected_name = item["raw"],
                confidence    = 1.0,
            )

        job.status = 'completed'
        job.completed_at = timezone.now()
        job.save(update_fields=['status', 'completed_at'])

    except Exception as e:
        job.status = 'failed'
        job.save(update_fields=['status'])
        raise e