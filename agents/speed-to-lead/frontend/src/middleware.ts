import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function middleware(request: NextRequest) {
  // DEV_SCREENSHOT_BYPASS: skip auth for local screenshot capture
  if (process.env.NEXT_PUBLIC_DEV_BYPASS_AUTH === "1") {
    if (request.nextUrl.pathname === "/login") {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }
    return NextResponse.next();
  }

  const supabaseUrl  = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const supabaseKey  = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim();

  // Skip auth if Supabase isn't configured yet (dev / local without keys)
  if (!supabaseUrl || !supabaseKey) {
    return NextResponse.next();
  }

  let response = NextResponse.next({ request });

  const supabase = createServerClient(supabaseUrl, supabaseKey, {
    cookies: {
      getAll() { return request.cookies.getAll(); },
      setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options),
        );
      },
    },
  });

  const { data: { user } } = await supabase.auth.getUser();
  const isLogin = request.nextUrl.pathname === "/login";

  if (!user && !isLogin) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if (user && isLogin) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
