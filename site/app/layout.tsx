import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://evidencegraph-datahub.liu891855.chatgpt.site"),
  title: "EvidenceGraph Assurance Studio — DataHub-native change assurance",
  description: "Traverse the full DataHub context graph, generate evidence-bound migration code, validate it in native runtimes, and fail closed when lineage is incomplete.",
  icons: { icon: "/favicon.svg", shortcut: "/favicon.svg" },
  openGraph: {
    type: "website",
    title: "EvidenceGraph Assurance Studio",
    description: "A schema change should not become an incident. See the complete impact graph, verified migration pack, and claim-level evidence ledger.",
    images: [{
      url: "/og.png",
      width: 1680,
      height: 945,
      alt: "EvidenceGraph turns incomplete repository analysis into a complete, evidence-backed DataHub impact graph.",
    }],
  },
  twitter: {
    card: "summary_large_image",
    title: "EvidenceGraph Assurance Studio",
    description: "DataHub-native change assurance with evidence before action.",
    images: ["/og.png"],
  },
};

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor: "#071019",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
