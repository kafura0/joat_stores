import type { BrandingData } from "@/types/branding";

import HeaderCentered from "@/components/layout/variants/HeaderCentered";
import HeaderSplit from "@/components/layout/variants/HeaderSplit";
import HeaderMinimal from "@/components/layout/variants/HeaderMinimal";

import FooterColumns from "@/components/layout/variants/FooterColumns";
import FooterSimple from "@/components/layout/variants/FooterSimple";
import FooterMinimal from "@/components/layout/variants/FooterMinimal";

type BrandingProps = { branding: BrandingData };

export function DynamicHeader({ branding, templateStyle }: BrandingProps & { templateStyle: string }) {
  switch (templateStyle) {
    case "classic":
      return <HeaderSplit branding={branding} />;
    case "minimal":
      return <HeaderMinimal branding={branding} />;
    case "bold":
    case "vibrant":
    default:
      return <HeaderCentered branding={branding} />;
  }
}

export function DynamicFooter({ branding, templateStyle }: BrandingProps & { templateStyle: string }) {
  switch (templateStyle) {
    case "classic":
      return <FooterSimple branding={branding} />;
    case "minimal":
      return <FooterMinimal branding={branding} />;
    case "bold":
    case "vibrant":
    default:
      return <FooterColumns branding={branding} />;
  }
}
