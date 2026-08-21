// import { Badge } from "@/components/ui/badge";
// import { ScrollArea } from "@/components/ui/scroll-area";
// import { cn } from "@/utils/cn";
// import { useNavigate } from "react-router-dom";
// import {
//   Card,
//   CardContent,
//   CardDescription,
//   CardHeader,
//   CardTitle,
// } from "@/components/ui/card";
// import { EmailRow } from "../data/schema";

// interface Email {
//   id: string;
//   subject: string;
//   sender: string;
//   preview: string;
//   timestamp: string;
//   priority: "high" | "medium" | "low";
//   intent: "inquiry" | "followup" | "support";
//   read: boolean;
//   mailbox: string;
//   confidenceScore?: number;
//   needsHumanEscalation?: boolean;
//   escalationReason?: string;
// }

// interface EmailListProps {
//   emails: EmailRow[];
//   selectedEmail: string | null;
//   onSelectEmail: (id: string) => void;
// }

// const EmailList: React.FC<EmailListProps> = ({
//   emails,
//   selectedEmail,
//   onSelectEmail,
// }) => {
//   const navigate = useNavigate();

//   const handleEmailClick = (emailId: string) => {
//     onSelectEmail(emailId);
//     navigate(`/email/${emailId}`);
//   };

//   return (
//     <ScrollArea className="h-[calc(100vh-4rem)]">
//       <div className="space-y-2 p-4">
//         {emails.map((email) => (
//           <Card
//             key={email.id}
//             onClick={() => handleEmailClick(email.id)}
//             className={cn(
//               "cursor-pointer transition-all duration-200",
//               "hover:shadow-md",
//               selectedEmail === email.id ? "border-primary" : "border-border",
//               !email.read && "bg-accent"
//             )}
//           >
//             <CardHeader className="p-4 pb-2">
//               <div className="flex items-center justify-between">
//                 <div className="flex items-center gap-2">
//                   <CardTitle className="text-sm font-medium">
//                     {email.sender}
//                   </CardTitle>
//                   <Badge
//                     variant="secondary"
//                     className={cn(
//                       "text-xs",
//                       email.priority === "high" && "bg-priority-high text-white",
//                       email.priority === "medium" &&
//                         "bg-priority-medium text-white",
//                       email.priority === "low" && "bg-priority-low text-white"
//                     )}
//                   >
//                     {email.priority}
//                   </Badge>
//                   <Badge
//                     variant="outline"
//                     className={cn(
//                       "text-xs",
//                       email.intent === "inquiry" && "text-intent-inquiry",
//                       email.intent === "followup" && "text-intent-followup",
//                       email.intent === "support" && "text-intent-support"
//                     )}
//                   >
//                     {email.intent}
//                   </Badge>
//                   <Badge variant="outline" className="text-xs">
//                     {email.mailbox}
//                   </Badge>
//                 </div>
//                 <span className="text-xs text-muted-foreground">
//                   {email.timestamp}
//                 </span>
//               </div>
//             </CardHeader>
//             <CardContent className="p-4 pt-2">
//               <CardTitle className="text-sm font-medium leading-none mb-2">
//                 {email.subject}
//               </CardTitle>
//               <CardDescription className="text-sm text-muted-foreground line-clamp-2">
//                 {email.preview}
//               </CardDescription>
//             </CardContent>
//           </Card>
//         ))}
//       </div>
//     </ScrollArea>
//   );
// };

// export default EmailList;