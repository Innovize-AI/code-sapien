import { columns } from "@/components/ui/inbox/components/columns";
import { DataTable } from "@/components/ui/inbox/components/data-table";
import { taskSchema } from "@/components/ui/inbox/data/schema";
import path from "path";
import { z } from "zod";
import { promises as fs } from "fs"
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Separator } from "@radix-ui/react-separator";

export default async function Page() {
  
  const tasks= await getTasks()
  console.log("tasks" , tasks)

    return (
          <div className="flex items-center gap-2 px-4">
            {/* <SidebarTrigger className="-ml-1" /> */}
            <Separator orientation="vertical" className="mr-2 h-4" />
            <DataTable data={tasks} columns={columns} />

            {/* <Breadcrumb>
              <BreadcrumbList>
                <BreadcrumbItem className="hidden md:block">
                  <BreadcrumbLink href="#">
                    Building Your Application
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator className="hidden md:block" />
                <BreadcrumbItem>
                  <BreadcrumbPage>Data Fetching</BreadcrumbPage>
                </BreadcrumbItem>
              </BreadcrumbList>
            </Breadcrumb> */}
          </div>
    )
  }

  async function getTasks() {
    const data = await fs.readFile(
      path.join(process.cwd(), "src/components/ui/inbox/data/tasks.json")
    )
  
    const tasks = JSON.parse(data.toString())
  
    return z.array(taskSchema).parse(tasks)
  }