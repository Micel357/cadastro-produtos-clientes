export type Product = {
  id: number;
  name: string;
  category: string;
  price: number;
  stock: number;
  description: string;
};

export type Client = {
  id: number;
  name: string;
  email: string;
  phone: string;
  city: string;
};

export type Dashboard = {
  products: number;
  clients: number;
  stock: number;
  inventory_value: number;
};
