# elearning

Project Structure

elearning/
├── elearning/                # project config
│   ├── asgi.py               # required for WebSockets
│   ├── settings.py
│   ├── urls.py
│   └── routing.py            # channels routing
│
├── apps/
│   ├── accounts/             # users, roles, profiles, search
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── api.py            # DRF user endpoints
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── tests.py
│   │   └── templates/accounts/
│   │       ├── login.html
│   │       ├── signup.html
│   │       └── profile.html
│   │
│   ├── courses/              # courses, enrolment, materials, feedback
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── api.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── tests.py
│   │   └── templates/courses/
│   │       ├── student_home.html
│   │       ├── teacher_home.html
│   │       ├── course_detail.html
│   │       └── course_create.html
│   │
│   ├── status/               # status updates (activity feed)
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── api.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── tests.py
│   │
│   ├── chat/                 # WebSocket real-time chat
│   │   ├── consumers.py
│   │   ├── routing.py
│   │   ├── models.py
│   │   ├── tests.py
│   │   └── templates/chat/
│   │       └── chat_room.html
│   │
│   ├── notifications/        # notifications (enrol, materials)
│   │   ├── models.py
│   │   ├── consumers.py      # websocket push
│   │   ├── signals.py
│   │   └── tests.py
│   │
│   └── core/                 # layout & shared UI
│       ├── views.py
│       ├── urls.py
│       └── templates/core/
│           └── base.html
│
├── static/
│   ├── js/
│   │   ├── search.js
│   │   ├── profile_modal.js
│   │   ├── chat.js
│   │   └── notifications.js
│   └── css/
│       └── main.css
│
└── manage.py