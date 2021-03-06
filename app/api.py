'''
-------------------------------------------------
    File name:    api.py
    Description:    api接口
    Author:     RGDZ
    Data:    2020/01/17 12:35:26
-------------------------------------------------
   Version:    v1.0
   Contact:    rgdz.gzu@qq.com
   License:    (C)Copyright 2020-2021
'''

from flask import Blueprint, request, jsonify
from functools import wraps

from .models import *



api = Blueprint("api", __name__)

class Code:
    """ 后台状态枚举类 """
    NULL = 0 # 什么都没有
    ERROR = 100 # 执行错误
    SUCCESS = 200 #成功
    NOT_ADMIN = 300 # 非管理员
    ADMIN_BUT_NOEXEC = 301 #是管理员，但未执行代码
    NOT_LOGIND = 400 #未登录
    LOGIND_BUT_NOEXEC = 401 # 已经验证登录，但未执行代码
    TOKEN_LOSE = 500 #Token 失效
    FLAG_ERROR = 600 # flag 错误
    FLAG_EXISTED = 700 # flag 已提交
    VERIFY_DATA = 800 # 验证数据
    VERIFYD_BUT_NOEXEC = 801 # 已验证数据，但未执行代码
    BAD_DATA = 900 # 坏数据
    NO_EXISTSED = 1000 # 数据不存在
    EXISTSED = 1001 #数据已存在

# 接口权限控制装饰器
def verify_data(func):
    """ 验证数据是否可靠，相当于waf层，TODO: 封装可扩展 """
    @wraps(func)
    def wrapper(*args, **kw):
        ret = {'code': Code.NULL}
        json_data = request.get_json(force=True)
        username = json_data.get('username')
        email = json_data.get('email')
        password = json_data.get('pass')
        if password and email or username:
            ret['code'] = Code.VERIFYD_BUT_NOEXEC
            return func(json_data, ret)
        ret['code'] = Code.BAD_DATA
        return jsonify(ret)
    return wrapper

def require_login(func):
    """ 登录控制 """
    @wraps(func)
    def wrapper(*args, **kw):
        ret={'code':Code.NOT_LOGIND}
        user_data = request.get_json(force=True).get('user')
        token = user_data.get('token')
        uid = user_data.get('uid')
        role = user_data.get('role')
        if token:
            user = User.verify_auth_token(token)
            if user and str(user.id)==uid and user.role==role:
                ret['code'] = Code.LOGIND_BUT_NOEXEC
                return func(user=user, ret=ret)
            ret['code'] = Code.TOKEN_LOSE
        return func(user=None, ret=ret)
    return wrapper

def admin(func):
    """ 管理员权限控制 """
    @wraps(func)
    def wrapper(user: User, ret: {}):
        if user:
            if user.isAdmin:
                ret['code'] = Code.ADMIN_BUT_NOEXEC
                return func(ret)
            ret['code'] = Code.NOT_ADMIN
        return jsonify(ret)
    return wrapper


# API接口

@api.route("/")
def index():
    return jsonify({"msg":"hello"})


@api.route("/login", methods=["POST"])
@verify_data
def login(json_data: {}, ret: {}):
    """ 登录接口
        请求数据:
        {
            "email":email,
            "pass":pass
        }
        返回数据:
        {
            "code":200,
            "user": {
                'uid':uid,
                'role:role,
                'name':name,
                'token':token
            }
        }
    """
    email = json_data.get('email')
    password = json_data.get('pass')
    user = User.objects(userEmail=email).first()
    if user:
        if user.verify_pass(password):
            ret["code"] = Code.SUCCESS
            ret['user']={
                'uid':str(user.id),
                'role':user.role,
                'name':user.userName,
                'token':user.token
            }
            return jsonify(ret)
        ret["code"] = Code.ERROR
        return jsonify(ret)
    return jsonify(ret)


@api.route("/register", methods=["POST"])
@verify_data
def register(json_data: {}, ret: {}):
    """ 注册接口
        请求数据:
        {
            "username": username,
            "email": email,
            "pass": password
        }
        返回数据:
        {
            "code":200,
            "user": {
                'uid':uid,
                'role:role,
                'name':name,
                'token':token
            }
        }
    """
    username = json_data.get('username')
    email = json_data.get('email')
    password = json_data.get('pass')
    if not User.isexist(username, email):
        user = User.init(username, email, password)
        ret['code'] = Code.SUCCESS
        ret['user']={
            'uid':str(user.id),
            'role': user.role,
            'name':user.userName,
            'token':user.token
        }
        return jsonify(ret)
    ret['code'] = Code.ERROR
    return jsonify(ret)

@api.route("/check_exists", methods=["GET"])
def check_exists():
    """ 检查用户名,邮箱是否存在 
        请求参数:
        ?value=value
        返回数据:
        {
            'code':200
        }
    """
    ret = {'code':Code.NULL}
    value = request.args.get('value')
    if User.isexist(username=value, email=value):
        ret['code'] = Code.EXISTSED # 用户已存在
        return jsonify(ret)
    ret['code'] = Code.NO_EXISTSED
    return jsonify(ret)

@api.route("/userInfo", methods=["GET"])
def userInfo():
    """ 获取用户信息接口 
        请求参数: ?uid=uid
        返回数据: 
        {
            'code':200,
            'userInfo':{
                'scoreData':scoreData,
                'score':score
                'scoreDFS':scoreDFS
            }
        }
    """
    ret={'code':Code.NULL, 'userInfo':{}}
    uid = request.args.get('uid')
    user = User.objects(pk=uid).first()
    if user:
        ret.update({
        'userInfo':{
            'name': user.userName,
            'scoreData':user.scoreData,
            'solvedStatic':user.solvedStatic,
            'score':user.score,
            'scoreDFS':{user.userName:user.scoreDFS}
        }
    })
    ret['code'] = Code.SUCCESS
    return jsonify(ret)


@api.route("/challenges", methods=["POST"])
@require_login
def challenges(user: User, ret: {}):
    """ 获取challenges数据接口 
        请求数据:
        {
            'ctype':'Pwn',
            'toke':'token' （可选）
        }
        返回数据:
        {
            "code":200,
            "challenges":[
                {
                    'cid':cid,
                    'type':type,
                    'title':title,
                    'des':des,
                    'socre':score,
                    'solved':solved (根据token)
                },
                ...
            ]
        }
    """
    ret['challenges'] = []
    ctype = request.get_json(force=True).get('ctype')
    challenges = Challenge.objects(tIdx=cTypes.index(ctype)).order_by("-createTime")
    for challenge in challenges:
        data = {
            'cid':str(challenge.id),
            'type':challenge.ctype,
            'title':challenge.title,
            'des': challenge.description,
            'score': challenge.score,
            'solvers': len(challenge.solvers),
            'solved': False
            }
        if user:
            data.update({'solved':challenge in user.solveds})
        ret['challenges'].append(data)
    return jsonify(ret)
        


@api.route("/submit_flag", methods=['POST'])
@require_login
def submit_flag(user: User, ret: {}):
    """ 提交flag接口 
        请求数据:
        {
            'token':token,
            'cid':cid,
            'flag':flag
        }
        返回数据:
        {
            "code":200,
        }
    """
    json_data = request.get_json(force=True)
    cid = json_data.get('cid')
    flag = json_data.get('flag')
    if user:
        challenge = Challenge.objects(pk=cid).first()
        ret['code'] = Code.FLAG_EXISTED
        if challenge not in user.solveds:
            ret['code'] = Code.FLAG_ERROR
            if challenge.verify_flag(flag):
                user.solved_challenge(challenge)
                ret['code'] = Code.SUCCESS
    return jsonify(ret)
    
    

@api.route('/add_challenge', methods=['POST'])
@require_login
@admin
def add_challenge(ret: {}):
    """ 添加题目接口 
        请求数据:
        {
            'token':token
            'type':type,
            'title':title,
            'des':des,
            'score':score,
            'flag':flag
        }
        返回数据:
        {
            "code":200,
        }
    """
    json_data = request.get_json(force=True)
    tIdx = cTypes.index(json_data.get('type'))
    title = json_data.get('title')
    des = json_data.get('des')
    score = json_data.get('score')
    flag = json_data.get('flag')
    Challenge.init(tIdx, title, des, score, flag)
    ret['code'] = Code.SUCCESS
    return jsonify(ret)


@api.route('/del_challenge', methods=['POST'])
@require_login
@admin
def del_challenge(ret: {}):
    """ 删除题目接口 
        请求数据:
        {
            'token':token,
            'cid':cid
        }
    """
    cid = request.get_json(force=True).get('cid')
    Challenge.objects(id=cid).first().delete()
    Challenge.objects(id=cid).delete()
    ret['code'] = Code.SUCCESS
    return jsonify(ret)


@api.route('/announcements', methods=['GET'])
def announcements():
    """ 获取公告信息接口 
        请求参数: /
        返回数据: 
        {
            'code':200,
            'anncs':[]
        }
    """
    ret = {
        'code':Code.NULL,
        'anncs':[]
    }
    for annc in Announcement.objects().order_by("-createTime"):
        ret['anncs'].append({
            'aid':str(annc.id),
            'title':annc.title,
            'body':annc.body,
            'createTime':annc.date
        })
    ret['code'] = Code.SUCCESS
    return jsonify(ret)


@api.route('/add_announcement', methods=['POST'])
@require_login
@admin
def add_announcement(ret: {}):
    """ 添加公告接口 
        请求数据: 
        {
            'token':token,
            'title':title,
            'body':body
        }
        返回数据:
        {
            'code':200,
        }
    """
    json_data = request.get_json(force=True)
    title = json_data['title']
    body = json_data['body']
    Announcement.init(title, body)
    ret['code'] = Code.SUCCESS
    return jsonify(ret)


@api.route('/del_announcement', methods=['POST'])
@require_login
@admin
def del_announcement(ret: {}):
    """ 删除公告接口 
        请求数据: 
        {
            'aid':aid
        }
        返回数据:
        {
            'code':200,
        }
    """
    aid = request.get_json(force=True).get('aid')
    Announcement.objects(pk=aid).delete()
    ret['code'] = Code.SUCCESS
    return jsonify(ret)


@api.route('/score_card', methods=["GET"])
def score_card():
    """ 计分板数据接口
        返回数据:
        {
            'code':200,
            'msg':success,
            'data':[
                {
                    'rank': 1,
                    'name': 'aaa',
                    'solved': 5,
                    'score': 900
                },
                ...
            ]
        }
    """
    ret = {'code':Code.NULL, 'table':[], 'top10':{}}
    ret['table'] = User.static()
    for idx in range(len(ret['table'])):
        if idx>10:
            break
        user = User.objects(pk=ret['table'][idx]['uid']).first()
        ret['top10'].update({user.userName:user.scoreDFS})
    ret['code'] = Code.SUCCESS
    return jsonify(ret)