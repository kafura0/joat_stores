export interface IProductVariant {
  id: string;
  name: string;
  price: string;
  sku: string | null;
  inventory_count: number;
  is_available: boolean;
}

export interface IProductImage {
  id: string;
  image: string;
  alt_text: string;
  position: number;
}

export interface IProduct {
  id: string;
  name: string;
  description: string;
  category: { id: string; name: string } | null;
  is_available: boolean;
  variants: IProductVariant[];
  images: IProductImage[];
}
