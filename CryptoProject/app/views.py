import base64
import os

from io import BytesIO
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, TableStyle
from reportlab.platypus import Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.models import PaintingRequest

import random
from datetime import timedelta

from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA384
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.http import HttpRequest
from django.views.generic import View

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.utils.datastructures import MultiValueDictKeyError

from .forms import *

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath("views.py")))

"""==============================="""
"""Roles and Permissions functions"""
"""==============================="""

# Paintor role tag
pnt_login_required = user_passes_test(lambda u: True if (not(u.is_superuser) and u.is_staff and u.is_active) else False, login_url='/')

def paintor_login_required(view_func):
    decorated_view_func = login_required(pnt_login_required(view_func), login_url='/')
    return decorated_view_func

# Client role tag
clt_login_required = user_passes_test(lambda u: True if (not(u.is_superuser) and not(u.is_staff) and u.is_active) else False, login_url='/')

def client_login_required(view_func):
    decorated_view_func = login_required(clt_login_required(view_func), login_url='/')
    return decorated_view_func

"""==============================="""
"""         Systems Views         """
"""==============================="""

class HomeView(View):
    template_name = 'app/home.html'
    context_name = 'Home Page'

    def get(self, request, format=None):
        """Renders the home page"""
        assert isinstance(request, HttpRequest)
        return render(
            request,
            self.template_name,
            {
                'title':self.context_name,
                })

##In this view a list of requests that the user has made will be shown
@client_login_required
@login_required(login_url='/')
def ordersList(request):

    #result = PaintingRequest.objects.filter(username=request.user.id).values()
    result = PaintingRequest.objects.filter(username=request.user.username).values()
    return render(request, 
        'app/requestsClient.html', 
        {
            'result':result,
            'title':'Orders',
            'year':datetime.now().year,
        })

@paintor_login_required
@login_required(login_url='/')
def ordersPainter(request):
    orders = PaintingRequest.objects.filter().values()
    orders_set = PaintingRequest.objects.filter().only('id','username')
    verify = []
    for order in orders_set:
        order_username = order.username
        order_id = order.id

        if not(verifying_process(order_username, order_id)):
            orders = orders.exclude(id=order_id)
    return render(request, 
        'app/ordersPainter.html', 
        {
            'result':orders,
            'title':'Orders',
            'year':datetime.now().year,
        })

@client_login_required
@login_required(login_url='/')
def newOrder(request):
    dt=""
    dd=""
    if request.method=="POST":
        dt = datetime.now()
        var = PaintingRequest(nameRequest=request.POST["nameRequest"],
        username=request.user.username,
        dateRequest=dt,
        description=request.POST["description"],
        image=request.FILES["image"],
        status='C',
        cost=random.randint(150,250)
        )
        dd = dt.date() + timedelta(days=30)
        var.save()
        getOrder(dt,dd,request)
        request
    return render(request,'app/newOrder.html',
        {
        'title':'New Order',
        'year':datetime.now().year,
        })

@paintor_login_required
@login_required(login_url='/')
def newDeliver(request):
    order = PaintingRequest.objects.filter(id=1).values()
    delivery = order[0]["dateRequest"].date() + timedelta(days=30)

    return render(request,'app/newDeliver.html',
        {
        'order':order,
        'title':'New Deliver',
        'year':datetime.now().year,
        'delivery':delivery
        })

@client_login_required
@login_required(login_url='/')
def welcome(request):
    return render(request,'app/mainClient.html',
        {
        'title':'Welcome',
        'year':datetime.now().year,
        })

@paintor_login_required
@login_required(login_url='/')
def welcomePainter(request):
    return render(request,'app/mainPainter.html',
        {
        'title':'Welcome',
        'year':datetime.now().year,
        })

"""==============================="""
"""       Functions System        """
"""==============================="""

def getOrder(dateTime,delivery,request):
    order = PaintingRequest.objects.filter(dateRequest=dateTime, username=request.user.username).values()
    generate_iv(order[0]["id"])
    generate_key(order[0]["id"])
    encrypt_image(order[0]["id"], BASE_DIR+"\\CryptoProject\\app\\static\\images\\"+order[0]["image"].replace("/","\\"))
    #delete the original image after encryption
    os.remove(BASE_DIR+"\\CryptoProject\\app\\static\\images\\"+order[0]["image"].replace("/","\\"))
    build_order_confirmation(order[0]["id"],order[0]["username"],
    order[0]["nameRequest"],order[0]["description"],order[0]["dateRequest"],
    delivery,order[0]["cost"])
    signing_process(order[0]["username"],order[0]["id"])


def build_order_confirmation(order_id, user_name, order_name, description, order_date, delivery_date, cost):
    oc = '' #text for the order confirmation
    oc = oc + str(datetime.now().date()) + '\n\n'
    oc = oc + 'Order Numbers: ' + str(order_id) + '\n\n'
    oc = oc + 'Order Details \n'
    oc = oc + '\tOrder Date: ' + str(order_date.date()) + '\n'
    oc = oc + '\tUser: ' + user_name + '\n'
    oc = oc + '\tOrder Name: ' + order_name + '\n'
    oc = oc + '\tDescription: ' + description + '\n\n'
    oc = oc + '\tDelivery Date: ' + str(delivery_date) + '\n\n'
    oc = oc + '\tTotal Cost: $'+ str(cost) + '.00 \n'
    
    order_confirmation_file = open(BASE_DIR+'\\CryptoProject\\app\\static\\orders\\'+str(order_id)+'_OrderConfirmation.txt','w')
    order_confirmation_file.write(oc)

def signing_process(user_id, order_id):
    """sign the order_confirmation"""
    order_file = open(BASE_DIR+'\\CryptoProject\\app\\static\\orders\\'+str(order_id)+'_OrderConfirmation.txt', 'r')
    order = order_file.read().encode()  #encode cast string to bytes
    private_key = RSA.import_key(open(BASE_DIR+'\\CryptoProject\\keys\\users\\'+str(user_id)+'_private.pem').read())
    h = SHA384.new(order)
    signature = pkcs1_15.new(private_key).sign(h)
    writeBinFile(signature, BASE_DIR+'\\CryptoProject\\app\\static\\orders\\'+str(order_id)+'_signature.bin')

def writeBinFile(file_bytes, file_name):
    """write a binary file in base64"""
    file = open(file_name, 'wb')
    file.write(base64.b64encode(file_bytes)) 
    file.close()
    
def readBinFile(file_name):
    """read a binary file in base64"""
    file = open(file_name, 'rb')
    file_bytes = file.read()
    file.close()
    return base64.b64decode(file_bytes)

def get_image_bytes(image_file_name):
    """get the bytes of an image file in base64"""
    image_file = open(image_file_name,'rb')
    image_bytes = image_file.read()
    return image_bytes

def build_image(image_name, image_bytes):
    """build an image from bytes"""
    file = open(image_name, 'wb')
    file.write(image_bytes) 
    file.close()

    file = open(image_name, 'rb')
    return file.read()

def generate_key(id):
    """generate a random key of 128 bits and store it in a file in base64"""
    key = get_random_bytes(16)
    writeBinFile(key, BASE_DIR + '\\CryptoProject\\keys\\orders\\' + str(id) + '_key.bin')
    
def generate_iv(id):
    """generate a random iv of 128 bits and store it in a file in base64"""
    iv = get_random_bytes(16)
    writeBinFile(iv, BASE_DIR + '\\CryptoProject\\keys\\orders\\' + str(id) + '_iv.bin')

def encrypt_image(id, image_file_name):
    """encrypt and store the client photo"""
    image_bytes = get_image_bytes(image_file_name)
    key = readBinFile(BASE_DIR + '\\CryptoProject\\keys\\orders\\' + str(id) + '_key.bin')
    iv = readBinFile(BASE_DIR + '\\CryptoProject\\keys\\orders\\' + str(id) + '_iv.bin')
    
    #build an AES cipher using OFB mode
    cipher = AES.new(key, AES.MODE_OFB, iv)
    #encrypt the images bytes
    cipher_image_bytes = cipher.encrypt(image_bytes)
    writeBinFile(cipher_image_bytes, BASE_DIR + '\\CryptoProject\\app\\static\\images\\originals\\' + str(id) + '.bin')

def decrypt_image(id, extension):
    """read and decrypt the client photo"""
    cipher_image = readBinFile(BASE_DIR + '\\CryptoProject\\app\\static\\images\\originals\\' + str(id) + '.bin')
    key = readBinFile(BASE_DIR + '\\CryptoProject\\keys\\orders\\' + str(id) + '_key.bin')
    iv = readBinFile(BASE_DIR + '\\CryptoProject\\keys\\orders\\' + str(id) + '_iv.bin')
    
    #build an AES cipher using OFB mode
    cipher = AES.new(key, AES.MODE_OFB, iv)
    #decrypt the cipher images bytes
    plain_image_bytes = cipher.decrypt(cipher_image)
    return plain_image_bytes
     #build_image(BASE_DIR + '\\CryptoProject\\app\\static\\images\\originals\\' + str(id) + '_decrypted.'+ extension, plain_image_bytes)

def generate_RSA_keys(id):
    """generate a RSA key pair and stored in .pem files"""
    key = RSA.generate(1024)
    private_key = key.export_key()
    prikey_file = open(BASE_DIR + '\\CryptoProject\\keys\\users\\' + id + '_private.pem', 'wb')
    prikey_file.write(private_key)
    public_key = key.publickey().export_key()
    pubkey_file = open(BASE_DIR+'\\CryptoProject\\keys\\users\\'+id+'_public.pem', 'wb')
    pubkey_file.write(public_key)


def verifying_process(user_id, order_id):
    """verifying"""
    public_key = RSA.import_key(open(BASE_DIR+'\\CryptoProject\\keys\\users\\'+str(user_id)+'_public.pem').read())
    order_file = open(BASE_DIR+'\\CryptoProject\\app\\static\\orders\\'+str(order_id)+'_OrderConfirmation.txt', 'r')
    order = order_file.read().encode() #encode cast string to bytes
    signature = readBinFile(BASE_DIR+'\\CryptoProject\\app\\static\\orders\\'+str(order_id)+'_signature.bin')
    h = SHA384.new(order)
    try:
        pkcs1_15.new(public_key).verify(h, signature)
        return True
    except (ValueError, TypeError):
        return False


"""==============================="""
"""         Image View            """
"""==============================="""

def viewOrder(request):
    if request.method == 'GET':
        order_id = request.GET.get('orderid')
        #response = HttpResponse(content_type='text/plain')

        order = PaintingRequest.objects.get(id=int(order_id))
        name = str(order.image.name)
        extension = name[(name.rfind('.')+1):]

        original_image = decrypt_image(order_id, extension)
        response = HttpResponse(original_image, content_type='image/'+extension)
        response['Content-Disposition'] = 'attachment; filename=%s' % name[(name.rfind('/')+1):]

        return response


"""==============================="""
"""         PDF Generation        """
"""==============================="""

def generar_orden(request):
    if request.method == 'GET':
        order_id = request.GET.get('orderid')
        username = request.GET.get('username')

        response = HttpResponse(content_type='application/pdf')
        pdf_name = "orders.pdf"
        #response['Content-Disposition'] = 'attachment; filename=%s' % pdf_name
        buffer = BytesIO()

        '''Drawing pdf logo'''
        pdf = canvas.Canvas(buffer)
        logo_image = BASE_DIR + '\\CryptoProject\\app\\static\\images\\art.PNG'
        pdf.drawImage(logo_image, 40, 680, 240, 180,preserveAspectRatio=True)
        '''Order Content '''
        #Establecemos el tamaño de letra en 16 y el tipo de letra Helvetica
        pdf.setFont("Helvetica-Bold", 16)
        #Dibujamos una cadena en la ubicación X,Y especificada
        pdf.drawString(320, 760, u"Order Confirmation")

        order = open(BASE_DIR + '\\CryptoProject\\app\\static\\orders\\' + str(order_id) + '_OrderConfirmation.txt', "r")
        height = 660
        width = 40
        pdf.setFont("Helvetica-Bold", 12)

        for line in order:
            pdf.drawString(width, height, line.strip().encode())
            height = height - 20

        shopping_image = BASE_DIR + '\\CryptoProject\\app\\static\\images\\shopping.jpg'
        pdf.drawImage(shopping_image, 330, 320, 250, 350, preserveAspectRatio=True)

        pdf.showPage()
        pdf.save()
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        return response
