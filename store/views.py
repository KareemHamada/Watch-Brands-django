from django.shortcuts import render
from django.http import JsonResponse
import json
import datetime
from .models import * 
from .utils import cookieCart, cartData, guestOrder
import requests
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q


def store(request):
    data = cartData(request)

    cartItems = data['cartItems']
    # order = data['order']
    # items = data['items']

    categories = Category.objects.all()
    products = Product.objects.all()


    pri = request.GET.get("p")
    if pri == "high":
        products = Product.objects.order_by("-price")
    else:
        products = Product.objects.order_by("price")

    q = request.GET.get("q")
    if q != None:
        products = Product.objects.filter(
            Q(category__name__icontains=q) |
            Q(name__icontains=q)
        )


    # num of pages
    p = Paginator(products, 5)
    # print(p.num_pages)
    page_num = request.GET.get("page", 1)
    try:
        page = p.page(page_num)
    except EmptyPage:
        page = p.page(1)

    numberOfPagesPaggination = p.num_pages

    context = {'products':page, 'cartItems':cartItems,'categories':categories,"numberOfPagesPaggination": numberOfPagesPaggination}

    return render(request, 'store/index.html', context)



def cart(request):
	data = cartData(request)
	cartItems = data['cartItems']
	order = data['order']
	items = data['items']

	context = {'items':items, 'order':order, 'cartItems':cartItems}
	return render(request, 'store/cart.html', context)

def checkout(request):
	data = cartData(request)
	
	cartItems = data['cartItems']
	order = data['order']
	items = data['items']

	context = {'items':items, 'order':order, 'cartItems':cartItems}
	return render(request, 'store/checkout.html', context)

def updateItem(request):
	data = json.loads(request.body)
	productId = data['product_id']
	action = data['action']
	# print('Action:', action)
	# print('Product:', productId)

	customer = request.user.customer
	product = Product.objects.get(id=productId)
	order, created = Order.objects.get_or_create(customer=customer, complete=False)

	orderItem, created = OrderItem.objects.get_or_create(order=order, product=product)

	if action == 'add':
		orderItem.quantity = (orderItem.quantity + 1)
	elif action == 'remove':
		orderItem.quantity = (orderItem.quantity - 1)

	orderItem.save()

	if orderItem.quantity <= 0:
		orderItem.delete()

	return JsonResponse('Item was added', safe=False)

def processOrder(request):
	transaction_id = datetime.datetime.now().timestamp()
	data = json.loads(request.body)
	# print(data["form"]["name"])
	if request.user.is_authenticated:
		customer = request.user.customer
		order, created = Order.objects.get_or_create(customer=customer, complete=False)
	else:
		customer, order = guestOrder(request, data)

	
	total = float(data['form']['total'])
	order.transaction_id = transaction_id
	data_for_items = cartData(request)

	if total == order.get_cart_total:
		order.complete = True
		print("order saved")
	order.save()

	shipping_created = ShippingAddress.objects.create(
		customer=customer,
		order=order,
		address=data['shipping']['address'],
		city=data['shipping']['city'],
		mobile=data['shipping']['mobile'],
	)


	# cartItems = data['cartItems']
	# order = data['order']
	items = data_for_items['items']
	
	order_items = ''
	for item in items:
		order_items += f'''
				Product : {item['product']['name']}
				Price : {item['product']['price']}
				Count : {item['quantity']}
		'''
	# order_items = 
	token = '5137466573:AAGbrOjrqi5SXh7UVI0qY5D6srncn34PiIU'
	chat_id = '1361729593'
	msg = f'''
			customer : {customer.name}
			Email : {data['form']['email']}
			mobile : {data['shipping']['mobile']}
			address : {data['shipping']['address']}
			city : {data['shipping']['city']}
			Date Time : {shipping_created.date_added}
			order : {order_items}

			items Count : {order.get_cart_items}
			Total : {order.get_cart_total}

	'''
	url = "https://api.telegram.org/bot"+ token + "/sendMessage"+ "?chat_id=" + chat_id + "&text=" + msg

	res = requests.get(url)
	if res.status_code==200:
		print('Successfully sent')
	else:
		print('ERROR: Could not send Message')

	return JsonResponse('Order submitted..', safe=False)


def productDetails(request, id):
	product = Product.objects.get(id=id)
	products = Product.objects.all()
	data = cartData(request)

	cartItems = data['cartItems']

	context = {"product": product,"cartItems":cartItems,"products":products}
	return render(request, "store/detail.html", context)


def manage_order(request):
	shippings = ShippingAddress.objects.all()
	length_sh = len(shippings)
	context = {"shippings":shippings,"length_sh":length_sh}
	return render(request,"store/process.html",context)