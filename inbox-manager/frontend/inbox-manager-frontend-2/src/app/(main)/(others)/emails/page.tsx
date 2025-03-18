'use client'

import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/utils/cn";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useNavigate } from "react-router-dom";
import { createClient } from "@/utils/supabase/server";
import { EmailRow, emailSchema } from "@/components/ui/inbox/data/schema";
// import EmailList from "@/components/ui/inbox/components/email-list";
import { Separator } from "@/components/ui/separator";
import { z } from "zod";


export default async function Page() {
  
  // interface EmailRow{
  //   subject: string,
  //   user_id:  string,
  //   sender_email: string,
  //   category: string,
  //   intent: string,
  //   pii_detected: boolean,
  //   preprocessed_email: string,
  //   requires_response: boolean,
  //   received_at: string,
  //   escalated_to_human: boolean,
  //   category_confidence_score:number,
  //   email_response_draft: string
  // }
      const supabase = createClient();

      const {
        data: { user },
      } = await supabase.auth.getUser();

      console.log("user", user?.email)
      let fetchedData: EmailRow[]=[]
      try {
        fetchedData = await getEmailsByUser(user?.email);
        console.log("Fetched data SERVER ACTION INGRESOS:", fetchedData);
      } catch (error) {
        console.error("Error fetching data SERVER ACTION INGRESOS:", error);
      }
    

    return (
          <div className="flex items-center gap-2 px-4">
            {/* <SidebarTrigger className="-ml-1" /> */}
            <Separator orientation="vertical" className="mr-2 h-4" />
            {/* <EmailList emails={fetchedData}/> */}
          </div>
    )
  }

  async function getEmailsByUser(email:string|undefined) {
    // const data = await fs.readFile(
    //   path.join(process.cwd(), "src/components/ui/inbox/data/tasks.json")
    // )
    const endpoint_url=  process.env.NEXT_PUBLIC_BACKEND_URL
    console.log("end point url", endpoint_url)
    if(email=== undefined){
      return []
    }
    console.log("email", email)
    const url = `${endpoint_url}/db-router/emails_of_user/?email_id=${email}`;
    console.log("url", url)
    const response= await fetch(url)

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const emails= await response.json()

    console.log("emails", emails)
    return z.array(emailSchema).parse(emails)
  }