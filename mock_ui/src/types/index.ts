export interface User {
  id: number
  email: string
  name: string
}

export interface AuthResponse {
  token: string
  userId: number
  name: string
}

export interface MenuItem {
  id: number
  name: string
  price: number
  description: string
  imageUrl?: string
}

export interface MenuCategory {
  categoryId: number
  categoryName: string
  items: MenuItem[]
}

export interface Restaurant {
  id: number
  name: string
  cuisine: string
  rating: number
  deliveryTime: number
  minimumOrder: number
  serviceTypes?: string[]
  districts?: string[]
  imageUrl?: string
}

export interface Market {
  id: number
  name: string
  rating: number
  deliveryTime: number
  minimumOrder: number
  category: string
  districts?: string[]
}

export interface AddressSuggestion {
  id: string
  label: string
  district: string
  city: string
}

export interface CartItem {
  itemId: number
  name: string
  price: number
  quantity: number
  restaurantId: number
  sourceType?: string
}

export interface Cart {
  items: CartItem[]
  total: number
  itemCount: number
}

export interface Order {
  orderId: string
  userId: number
  restaurantId: number
  items: CartItem[]
  total: number
  deliveryAddress: string
  paymentMethod: string
  status: string
  statusIndex: number
}
