"use server";

import { createClient } from "@/utils/supabase/server";
import { revalidatePath } from "next/cache";
import { redirect, RedirectType } from "next/navigation";

export async function signOut() {
  const supabase = createClient();

  await supabase.auth.signOut();
  
  redirect("/",RedirectType.replace)

  // revalidatePath("/", "layout");
}
