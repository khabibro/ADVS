import { Card } from "@advs/ui";

const types = ["GRADUATION_CERTIFICATE", "CAREER_CERTIFICATE", "BUSINESS_REGISTRATION_CERTIFICATE", "SME_CONFIRMATION_CERTIFICATE"];

export default function DocumentTypesPage() {
  return <section className="space-y-4"><h1 className="text-2xl font-semibold">문서 유형</h1>{types.map((type) => <Card key={type}>{type}</Card>)}</section>;
}

