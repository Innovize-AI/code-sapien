import Footer from "@/components//footer";
import Navbar from "@/components//navbar";
import { AppSidebar } from "@/components/app-sidebar";
import { Sidebar, SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { SupabaseAuthClient } from "@supabase/supabase-js/dist/module/lib/SupabaseAuthClient";
import { Breadcrumb, BreadcrumbList, BreadcrumbItem, BreadcrumbLink, BreadcrumbSeparator, BreadcrumbPage } from "@/components/ui/breadcrumb";
import { columns } from "@/components/ui/inbox/components/columns";
import { DataTable } from "@/components/ui/inbox/components/data-table";

import { promises as fs } from "fs"
import path from "path"
import { taskSchema } from "@/components/ui/inbox/data/schema";
import { z } from "zod";

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {

  // const tasks= await getTasks()
  // console.log("tasks" , tasks)
  return (
    <>
      {/* <Footer /> */}
       <AppSidebar />
       <SidebarInset>
          <main className="container p-4 sm:p-6 flex-1">{children}</main>
       </SidebarInset>
      {/* <SidebarTrigger className="-ml-1" />
      <SidebarInset>
        <header className="flex h-16 shrink-0 items-center gap-2 transition-[width,height] ease-linear group-has-[[data-collapsible=icon]]/sidebar-wrapper:h-12">
          <div className="flex items-center gap-2 px-4">
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="mr-2 h-4" />
            <h3>Profile Page</h3>
              <Breadcrumb>
              <BreadcrumbList>
                <BreadcrumbItem className="hidden md:block">
                  <BreadcrumbLink href="#">
                    Building Your Application+
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator className="hidden md:block" />
                <BreadcrumbItem>
                  <BreadcrumbPage>Data Fetching</BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb> 
            <DataTable data={tasks} columns={columns} />
          </div>
        </header>
          <div className="flex flex-1 flex-col gap-4 p-4 pt-0">
          <div className="grid auto-rows-min gap-4 md:grid-cols-3">
            <div className="aspect-video rounded-xl bg-muted/50" />
            <div className="aspect-video rounded-xl bg-muted/50" />
            <div className="aspect-video rounded-xl bg-muted/50" />
          </div>
          <div className="min-h-[100vh] flex-1 rounded-xl bg-muted/50 md:min-h-min" />
        </div>
      </SidebarInset>  */}
    </>
  );
}

// async function getTasks() {
//   const data = await fs.readFile(
//     path.join(process.cwd(), "src/components/ui/inbox/data/tasks.json")
//   )

//   const tasks = JSON.parse(data.toString())

//   return z.array(taskSchema).parse(tasks)
// }
