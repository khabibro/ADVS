import type { OverallStatus } from "./types";

export const DATE_OPERATORS = [
  { value: "ON_OR_BEFORE", label: "이전 (같은 날 포함)" },
  { value: "ON_OR_AFTER", label: "이후 (같은 날 포함)" },
] as const;

export const NUMBER_OPERATORS = [
  { value: "GREATER_THAN_OR_EQUAL", label: "이상" },
  { value: "LESS_THAN_OR_EQUAL", label: "이하" },
  { value: "EQUALS", label: "같음" },
] as const;

export const VALUE_TYPES = [
  { value: "string", label: "이름·텍스트", hint: "띄어쓰기, (주)·주식회사 같은 표기 차이는 무시" },
  { value: "identifier", label: "번호·날짜", hint: "하이픈과 공백을 빼고 숫자만 비교" },
  { value: "institution", label: "학교·기관명", hint: "'대학교' 같은 일반 명칭과 한 글자 차이는 확인 필요로 처리" },
] as const;

export const STATUS_LABELS: Record<OverallStatus, string> = {
  READY: "제출 가능",
  REVIEW_REQUIRED: "확인 필요",
  NEEDS_CORRECTION: "보완 필요",
};

export function operatorLabel(operator: string): string {
  return (
    [...DATE_OPERATORS, ...NUMBER_OPERATORS].find((item) => item.value === operator)?.label ?? operator
  );
}

export function valueTypeLabel(value: string | undefined): string {
  return VALUE_TYPES.find((item) => item.value === (value ?? "string"))?.label ?? "이름·텍스트";
}

const DATE_TIME = new Intl.DateTimeFormat("ko-KR", {
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "-" : DATE_TIME.format(parsed);
}

export const WEB_URL = (process.env.NEXT_PUBLIC_WEB_URL ?? "http://localhost:3000").replace(/\/$/, "");
