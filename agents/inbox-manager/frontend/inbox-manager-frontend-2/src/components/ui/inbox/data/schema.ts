import { z } from "zod"

// We're keeping a simple non-relational schema here.
// IRL, you will have a schema for your data models.
export const emailSchema = z.object({
  // id: z.string(),
  // title: z.string(),
  // status: z.string(),
  // label: z.string(),
  // priority: z.string(),

  subject: z.string().nullable(),
  sender_email:z.string(),
  category: z.string(),
  intent:z.string(),
  pii_detected: z.boolean(),
  preprocessed_email:z.string(),
  requires_response:z.boolean(),
  escalated_to_human:z.boolean(),
  category_confidence_score: z.number(),
  email_response_draft:z.string(),
  thread_id:z.string(),
  email_sent:z.boolean()

})

export type EmailRow = z.infer<typeof emailSchema>

