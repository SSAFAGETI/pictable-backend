from .models import Notification

def create_notification(receiver, actor, type, title, message, recipe=None, comment=None):
    # 자기 자신한테는 알림 안 보냄
    if receiver == actor:
        return

    Notification.objects.create(
        receiver=receiver,
        actor=actor,
        type=type,
        title=title,
        message=message,
        recipe=recipe,
        comment=comment,
    )

def notify_welcome(user):
    Notification.objects.create(
        receiver=user,
        actor=None,
        type='system',
        title='찰칵밥상에 오신 걸 환영해요',
        message='내 레시피를 등록하고 좋아요, 댓글, 알림을 받아보세요.',
    )

def notify_like(actor, recipe):
    create_notification(
        receiver=recipe.author,
        actor=actor,
        type='like',
        title='좋아요',
        message=f'{actor.nickname}님이 회원님의 레시피를 좋아합니다.',
        recipe=recipe,
    )

def notify_comment(actor, recipe, comment):
    create_notification(
        receiver=recipe.author,
        actor=actor,
        type='comment',
        title='댓글',
        message=f'{actor.nickname}님이 댓글을 남겼습니다.',
        recipe=recipe,
        comment=comment,
    )

def notify_reply(actor, recipe, comment):
    create_notification(
        receiver=comment.author,
        actor=actor,
        type='reply',
        title='답글',
        message=f'{actor.nickname}님이 답글을 남겼습니다.',
        recipe=recipe,
        comment=comment,
    )

def notify_follow(actor, receiver):
    create_notification(
        receiver=receiver,
        actor=actor,
        type='follow',
        title='팔로우',
        message=f'{actor.nickname}님이 회원님을 팔로우했습니다.',
    )