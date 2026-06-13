from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse
from .models import Customer, Restaurant, Item, Cart, CartItem, SupportTicket, Order, OrderItem

import razorpay
from django.conf import settings

# Create your views here.
def say_hello(request):
    return render(request, "index.html")
    # return HttpResponse("Say Hello my app is working!")

def open_signin(request):
    return render(request, "signin.html")

def open_signup(request):
    return render(request, "signup.html")

def signup(request):
    if request.method == 'POST': 
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        mobile =request.POST.get('mobile')
        address = request.POST.get('address')
        try:
            Customer.objects.get(username = username)
            return HttpResponse("Oops! Someone else grabbed that name first")
        except:
            Customer.objects.create(
                username = username,
                password = password,
                email = email,
                mobile = mobile,
                address = address,
            )
        return render(request, 'signin.html')

def signin(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

    try:
        Customer.objects.get(username = username, password = password)
        if username == 'adminleela':
            return render(request,'admin_home.html') 
        else:
            return redirect('customer_home', username=username)
    except Customer.DoesNotExist:
        return render(request, 'fail.html') 

from django.db.models import Q

def customer_home(request, username):
    restaurants = Restaurant.objects.all()

    return render(request, 'customer_home.html', {
        'restaurantList': restaurants,
        'username': username,
    }) 

def open_add_restaurant(request):
    return render(request, 'add_restaurant.html')

def add_restaurant(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        picture = request.POST.get('picture')
        cuisine = request.POST.get('cuisine')
        rating = request.POST.get('rating')

        if Restaurant.objects.filter(name = name).exists():
            return HttpResponse("Duplicate restaurant!")
        else:
            Restaurant.objects.create(
                name = name,
                picture = picture,
                cuisine = cuisine,
                rating = rating,
            )
    return render(request, 'admin_home.html')


def open_show_restaurant(request):
    restaurantList = Restaurant.objects.all()
    return render(request, 'show_restaurants.html',{"restaurantList" : restaurantList})

def open_update_restaurant(request, restaurant_id):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    return render(request, 'update_restaurant.html', {"restaurant" : restaurant})

def update_restaurant(request, restaurant_id):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    if request.method == 'POST':
        name = request.POST.get('name')
        picture = request.POST.get('picture')
        cuisine = request.POST.get('cuisine')
        rating = request.POST.get('rating')

        restaurant.name = name
        restaurant.picture = picture
        restaurant.cuisine = cuisine
        restaurant.rating = rating

        restaurant.save()

    restauranList = Restaurant.objects.all()
    return render(request, 'show_restaurants.html',{"restaurantList" : restauranList})

def delete_restaurant(request, restaurant_id):
    restaurant = Restaurant.objects.get(id = restaurant_id)
    restaurant.delete()

    restaurantList = Restaurant.objects.all()
    return render(request, 'show_restaurants.html', {"restaurantList" : restaurantList})

def open_update_menu(request, restaurant_id):
    restaurant = Restaurant.objects.get(id=restaurant_id)
    itemList = restaurant.items.all()
    return render(request, 'update_menu.html', {"itemList": itemList, "restaurant": restaurant})


def update_menu(request, restaurant_id):
    restaurant = Restaurant.objects.get(id=restaurant_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        vegeterian = request.POST.get('vegetarian') == 'on'
        picture = request.POST.get('picture')

        try:
            Item.objects.get(name=name)
            return HttpResponse("Duplicate item!")
        except Item.DoesNotExist:
            Item.objects.create(
                restaurant=restaurant,
                name=name,
                description=description,
                price=price,
                vegeterian=vegeterian,
                picture=picture,
            )

    return render(request, 'admin_home.html')

def view_menu(request, restaurant_id, username):
    restaurant = Restaurant.objects.get(id=restaurant_id)
    itemList = restaurant.items.all()
    # itemList = Item.objects.all()
    return render(request,'customer_menu.html',{"itemList" : itemList,"restaurant" : restaurant,"username" : username})

def add_to_cart(request, item_id, username):
    item = Item.objects.get(id=item_id)
    customer = Customer.objects.get(username=username)

    cart, created = Cart.objects.get_or_create(customer=customer)

    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, item=item)
    if not item_created:
        cart_item.quantity += 1
        cart_item.save()

    return HttpResponse('added to cart')

def show_cart(request, username):
    customer = Customer.objects.get(username=username)
    cart = Cart.objects.filter(customer=customer).first()
    cart_items = cart.cart_items.all() if cart else []
    total_price = cart.total_price() if cart else 0

    return render(request, "cart.html", {
        "cart_items": cart_items, 
        "total_price": total_price, 
        "username": username
    })

def checkout(request, username):
    # Fetch customer and their cart
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()
    cart_items = cart.cart_items.all() if cart else []
    total_price = cart.total_price() if cart else 0

    if total_price == 0:
        return render(request, 'checkout.html', {
            'error': 'Your cart is empty!',
        })
  
    # Initialize Razorpay client
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    # Avoid failing through system proxy env vars in local dev.
    client.session.trust_env = False

    # Create Razorpay order
    order_data = {
        'amount': int(total_price * 100),  # Amount in paisa
        'currency': 'INR',
        'payment_capture': '1',  # Automatically capture payment
    }

    try:
        order = client.order.create(data=order_data)
    except Exception:
        return render(request, 'checkout.html', {
            'username': username,
            'cart_items': cart_items,
            'total_price': total_price,
            'error': 'Payment service is currently unreachable. Please check your internet/proxy settings and try again.',
        })
    
    # Pass the order details to the frontend
    return render(request, 'checkout.html', {
        'username': username,
        'cart_items': cart_items,
        'total_price': total_price,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'order_id': order['id'],  # Razorpay order ID
        'amount_paise': order['amount'],
    })

# Orders Page
def orders(request, username):
    customer = get_object_or_404(Customer, username=username)
    cart = Cart.objects.filter(customer=customer).first()

    # Fetch cart items and total price before clearing the cart
    # Using list() forces immediate evaluation so items aren't lost when cleared below
    cart_items = list(cart.cart_items.all()) if cart else []
    total_price = cart.total_price() if cart else 0

    if cart and cart_items:
        # Create persistent Order record
        order = Order.objects.create(
            customer=customer,
            total_price=total_price,
            status="Preparing"
        )
        # Create OrderItem record for each cart item
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                item=cart_item.item,
                price=cart_item.item.price,
                quantity=cart_item.quantity
            )
        
        # Clear the cart after successfully recording the order
        cart.cart_items.all().delete()

    return render(request, 'orders.html', {
        'username': username,
        'customer': customer,
        'cart_items': cart_items,
        'total_price': total_price,
    })


def increase_quantity(request, cart_item_id):
    cart_item = get_object_or_404(CartItem, id=cart_item_id)
    cart_item.quantity += 1
    cart_item.save()
    return redirect('show_cart', username=cart_item.cart.customer.username)


def decrease_quantity(request, cart_item_id):
    cart_item = get_object_or_404(CartItem, id=cart_item_id)
    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
    else:
        cart_item.delete()
    return redirect('show_cart', username=cart_item.cart.customer.username)


def delete_cart_item(request, cart_item_id):
    cart_item = get_object_or_404(CartItem, id=cart_item_id)
    username = cart_item.cart.customer.username
    cart_item.delete()
    return redirect('show_cart', username=username)


def open_support(request, username):
    return render(request, 'support.html', {'username': username})


def submit_ticket(request, username):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        SupportTicket.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message
        )
        return render(request, 'support.html', {'username': username, 'success': True})
    return render(request, 'support.html', {'username': username})


def admin_tickets(request):
    tickets = SupportTicket.objects.all().order_by('-created_at')
    return render(request, 'admin_tickets.html', {'tickets': tickets})


def resolve_ticket(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    ticket.is_resolved = True
    ticket.save()
    return redirect('admin_tickets')


def delete_ticket(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    ticket.delete()
    return redirect('admin_tickets')


def order_history(request, username):
    customer = get_object_or_404(Customer, username=username)
    orders = Order.objects.filter(customer=customer).order_by('-created_at')
    return render(request, 'order_history.html', {
        'orders': orders,
        'username': username
    })


def reorder(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    customer = order.customer
    cart, created = Cart.objects.get_or_create(customer=customer)

    # Copy items from the past order to the active cart
    for order_item in order.order_items.all():
        cart_item, item_created = CartItem.objects.get_or_create(cart=cart, item=order_item.item)
        if not item_created:
            cart_item.quantity += order_item.quantity
        else:
            cart_item.quantity = order_item.quantity
        cart_item.save()

    return redirect('show_cart', username=customer.username)


def open_edit_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    return render(request, 'edit_item.html', {'item': item})


def edit_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        vegeterian = request.POST.get('vegetarian') == 'on'
        picture = request.POST.get('picture')

        # Prevent duplicate item names (consistent with the add item validation)
        if Item.objects.filter(name=name).exclude(id=item_id).exists():
            return HttpResponse("Duplicate item!")

        item.name = name
        item.description = description
        item.price = float(price) if price else 0.0
        item.vegeterian = vegeterian
        item.picture = picture
        item.save()

    return redirect('open_update_menu', restaurant_id=item.restaurant.id)


def delete_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    restaurant_id = item.restaurant.id
    item.delete()
    return redirect('open_update_menu', restaurant_id=restaurant_id)


