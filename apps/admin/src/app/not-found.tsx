import Link from "next/link";

export default function NotFound() {
  return (
    <div className="py-20 text-center">
      <h1 className="text-xl font-semibold">페이지를 찾을 수 없습니다</h1>
      <p className="mt-2 text-sm text-muted-foreground">주소가 바뀌었거나 삭제된 페이지입니다.</p>
      <Link className="mt-4 inline-block text-sm font-medium text-primary hover:underline" href="/">
        대시보드로 가기
      </Link>
    </div>
  );
}
