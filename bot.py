#!/usr/bin/env python

import sys
sys.path.append("./libs")
import os
import requests
import base64
import json
import logging
from enum import Enum

DEFAULT_API_VERSION = 4.0

## messaging types: "RESPONSE", "UPDATE", "MESSAGE_TAG"
# 푸시가 가는지 레귤러인지 구분
class NotificationType(Enum):
    regular = "REGULAR"
    silent_push = "SILENT_PUSH"
    no_push = "no_push"

# 래퍼클래스(헬퍼함수들이다.)
class Bot:

    def __init__(self, access_token, **kwargs):

        # 받은 액세스토큰을 가지고 인증을 하는부분이다.
        self.access_token = access_token
        self.api_version = kwargs.get('api_version') or DEFAULT_API_VERSION
        # 페이스북에게 api요청을 통해서 사용한다
        self.graph_url = 'https://graph.facebook.com/v{0}'.format(self.api_version)

    @property
    def auth_args(self):
        if not hasattr(self, '_auth_args'):
            auth = {
                'access_token': self.access_token
            }
            self._auth_args = auth
        return self._auth_args

    #메세지를 보내는함수
    def send_message(self, recipient_id, payload, notification_type, messaging_type, tag):

        # 페이로드에서 메세지 보낸 사용자 이이디를 받아서 딕셔너리형태로 입력받고
        payload['recipient'] = {
            'id': recipient_id
        }
        #메세지 타입을 입력 받고
        #payload['notification_type'] = notification_type
        payload['messaging_type'] = messaging_type

        # 테그가 NONE이 아닌 다른 값이 있으면 태그도 넣어주고
        if tag is not None:
            payload['tag'] = tag

        # 사용자의 graph_url을 입력받아 엔드포인트 {0}/me/message 만들어주고
        request_endpoint = '{0}/me/messages'.format(self.graph_url)

        # post요청을 엔드포인트, auth_args(토큰),페이로드를 합쳐서 response로 만들어 주고
        response = requests.post(
            request_endpoint,
            params = self.auth_args,
            json = payload
        )

        #페이로드 로그기록 남겨주고
        logging.info(payload)
        
        #제이슨형태로 반환한다.
        return response.json()

        # 사용자 아이디, NotificationType(reqgular)(이건 페이스북에서 필요) 메세지타입(응답), 태그는 None으로
    def send_text(self, recipient_id, text, notification_type = NotificationType.regular, messaging_type = 'RESPONSE', tag = None):
        
        # send_message의 외쪽 함수 (데코레이터 개념), 처음에 보낼때 파라미터들을 가공해서 다시파라미터로  send_message에넣어준다.
        # https://developers.facebook.com/docs/messenger-platform/send-messages/template/generic/#payload 여기 잘 나와있다.
        return self.send_message(
            recipient_id,
            {
                "message": {
                    "text": text
                }
            },
            notification_type,
            messaging_type,
            tag
        )
    
    # 실제 요청된 질의에  답변(send_text) 보내기 이전에 퀵어플라이 형식 또한 있다.
    # 위의send_text와 다르게 "quick_replies": quick_replies 만 추가된다.

    def send_quick_replies(self, recipient_id, text, quick_replies, notification_type = NotificationType.regular, messaging_type = 'RESPONSE', tag = None):

        return self.send_message(
            recipient_id,
            {
                "message":{
                    "text": text,
                    "quick_replies": quick_replies
                }
            },
            notification_type,
            messaging_type,
            tag
        )
    # 제네릭 템플릿으로(이미지 url이 있는 답변메시지) 보낼때 쓰는  wrapper함수
    # https://developers.facebook.com/docs/messenger-platform/send-messages/template/generic
    def send_attachment(self, recipient_id, attachment_type, payload, notification_type = NotificationType.regular, messaging_type = 'RESPONSE', tag = None):

        return self.send_message(
            recipient_id,
            {
                "message": {
                    "attachment":{
                        "type": attachment_type,
                        "payload": payload
                    }
                }
            },
            notification_type,
            messaging_type,
            tag
        )

    def send_action(self, recipient_id, action, notification_type = NotificationType.regular, messaging_type = 'RESPONSE', tag = None):

        return self.send_message(
            recipient_id,
            {
                "sender_action": action
            },
            notification_type,
            messaging_type,
            tag
        )

    def whitelist_domain(self, domain_list, domain_action_type):

        payload = {
            "setting_type": "domain_whitelisting",
            "whitelisted_domains": domain_list,
            "domain_action_type": domain_action_type
        }

        request_endpoint = '{0}/me/thread_settings'.format(self.graph_url)

        response = requests.post(
            request_endpoint,
            params = self.auth_args,
            json = payload
        )

        return response.json()
    # 처음에 메신저를 켰을때 어떤식으로 기본 템플릿을 보내는지
    def set_greeting(self, template):

        request_endpoint = '{0}/me/thread_settings'.format(self.graph_url)

        response = requests.post(
            request_endpoint,
            params = self.auth_args,
            json = {
                "setting_type": "greeting",
                "greeting": {
                    "text": template
                }
            }
        )

        return response

    def set_get_started(self, text):

        request_endpoint = '{0}/me/messenger_profile'.format(self.graph_url)

        response = requests.post(
            request_endpoint,
            params = self.auth_args,
            json = {
                "get_started":{
                    "payload": text
                }
            }
        )

        return response

    def get_get_started(self):

        request_endpoint = '{0}/me/messenger_profile?fields=get_started'.format(self.graph_url)

        response = requests.get(
            request_endpoint,
            params = self.auth_args
        )

        return response

    def get_messenger_profile(self, field):

        request_endpoint = '{0}/me/messenger_profile?fields={1}'.format(self.graph_url, field)

        response = requests.get(
            request_endpoint,
            params = self.auth_args
        )

        return response


    def upload_attachment(self, url):

        request_endpoint = '{0}/me/message_attachments'.format(self.graph_url)

        response = requests.post(
            request_endpoint,
            params = self.auth_args,
            json = {
                "message":{
                    "attachment":{
                        "type": "image",
                        "payload": {
                            "is_reusable": True,
                            "url": url
                        }
                    }
                }
            }
        )

        return response
