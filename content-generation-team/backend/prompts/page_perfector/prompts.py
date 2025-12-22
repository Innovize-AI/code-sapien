from langchain.prompts import PromptTemplate


PAGE_ANALYZER_PROMPT='''
**Objective:** To create a superior, higher-ranking webpage based on a competitor's page and specified keywords. Complete with instructions for designers and developers to create the page.

**Input**
Target Keywords: {target_keywords};
Page HTML:{scrape_webpage_content};

**Instructions:**

**1. Analysis of Competitor Page:**

*   **Content Analysis:**
    *   Extract the main topics and subtopics covered on the competitor's page.
    *   Identify the competitor's target audience and their apparent needs.
    *   Analyze the competitor's content structure (headings, subheadings, paragraphs, lists, etc.).
    *   Assess the competitor's content tone and style (formal, informal, technical, etc.).
    *   Identify any calls to action (CTAs) used by the competitor.
    *   Determine the competitor's use of internal and external links.
    *   Evaluate the competitor's use of images, videos, and other media.
    *   Analyze the competitor's keyword usage and density.
    *   Identify any content gaps or areas for improvement.
*   **SEO Analysis:**
    *   Analyze the competitor's page title, meta description, and header tags.
    *   Identify the competitor's target keywords and their variations.
    *   Identify any on-page SEO issues.
    
    
**2. Content Strategy:**

*   **Content Enhancement:**
    *   Based on the analysis, write content for a new page that is more comprehensive and informative than the competitor's page. Instead of using the competitor's company name, use (BRAND) as a placeholder. Brands that aren't the competitor's company name are safe to use.
    *   Identify specific areas where the new content can provide more value to the user.
    *   Incorporate the target keywords naturally and effectively.
    *   Add additional relevant topics or subtopics that the competitor's page missed.
    *   Determine potential questions that the new content should answer and answer them with detail.
    *   Use a content tone and style that is appropriate for the target audience.
    *   Provide specific factional examples, case studies, or statistics that can be used to support the content. Do not make up any fake or fictitious examples, case studies, or statistics. They must be verifiable from the text I have provided you with.
*   **Keyword Optimization:**
    *   Determine primary and secondary keywords to be used in the new content and incorporate them.
    *   Add keywords in an SEO friendly manner (title, headings, body, etc.).
    *   Ensure that the keyword usage is natural and not over-optimized.
    *   Use long-tail keywords that can be targeted in the new content.
*   **Call to Action (CTA):**
    *   Develop clear and compelling CTAs that encourage users to take the desired action.
    *   Determine the best specific placement for the CTAs on the page.
'''


PAGE_ANALYZER_PROMPT_TEMPLATE = PromptTemplate(
    input_variables=["target_keywords", "scrape_webpage_content"],
    template=PAGE_ANALYZER_PROMPT
)

DESIGN_INSTRUCTIONS_PROMPT= """
Review the layout of the competing page and provide text-based instructions on how to create a similar page. Capturing key UI/UX elements to create an engaging and high converting page.

**Design and Development Instructions:**

*   **Page Structure:**
    *   Specify the desired visual hierarchy of the page.
    *   Suggest the use of specific design elements (e.g., images, videos, infographics).
*   **Design Elements:**
    *   Specify the desired color palette, typography, and imagery style.
    *   Provide examples of design elements that are visually appealing and user-friendly.
    *   Ensure that the design is consistent with the brand's identity.
    *   Suggest the use of specific design tools or resources.
*   **User Experience (UX):**
    *   Provide instructions for creating a user-friendly and intuitive page.
    *   Ensure that the page is easy to navigate and understand.
    *   Suggest the use of specific UX practices.
    *  Provide instructions to ensure the page follows conversion rate optimization best practices.
    
**Output Format:**

Respond in markdown without using ```markdown as it causes the formatting to break

*   The output should be structured into the following sections:
    *   **Design Instructions:** (Page structure, design elements, technical specifications)
    *   **Development Instructions:** (Technical requirements, SEO recommendations)
*   Each section should be clearly labeled and easy to understand.
*   The output should be in Markdown format so that can be easily exported and shared with the designer and developer

Page To Reference: {scrape_webpage_content}

Please also reference the page analysis of the web page here: {page_analysis}


"""

DESIGN_INSTRUCTIONS_PROMPT_TEMPLATE= PromptTemplate(
    input_variables=["scrape_webpage_content","page_analysis"],
    template= DESIGN_INSTRUCTIONS_PROMPT
)


DRAFTER_PROMPT="""

You are an SEO content writer. You turn content briefs into written content based strictly on the specifications provided. You cover every detail requested. And you follow guidelines with perfection. You write incredibly detailed high quality content.

Before beginning, review the information about the client you are writing for as well as the Content Brand Guidelines provided below.

After reviewing the information about the client and familiarizing yourself with the brand guidelines, Review the target keyword and then the content outline. Then, write the content. Satisfy all requirements of the content outline. You must also follow the specifications below. Only output content for the article.

Title:
Select a page title and H1 that appears to be most optimized to match the search intent of the target keyword. Annotate with H1 and Title.

Body:
Follow the heading outline provided in the heading ideas section. Write the content with the goal of incorporating the keyword, entity, and semantic search ideas provided. Annotate headings with H2,H3,H4.

Review the additional topic ideas section and incorporate ideas that best match the search intent and goals provided in the content brief. Add this additional topic section to the page where it seems most relevant and appropriate.

Review the EEAT ideas section and incorporate all ideas provided. You must incorporate every single idea provided no matter what. Use only real examples provided instead of fictitious examples.

Review the FAQ ideas section and build out informative and insightful answers.


Additional:
Review the competitor summary to identify how to make a better page than theirs.
Instead of using definition lists, an H3 for a subheading, and then add details about the topic in a paragraph below it. This provides a more natural content format.

Do not use definition lists with colons and bold text preceding descriptions.

—

Here are Brand guidelines you must strictly follow: {keyword_knowledge}; 
Here is the About the client information to review: {brand_knowledge};

Target keyword(s): {target_keywords}.
Content outline: {page_analysis};
Ensure the layout matches these design instructions: {design_instructions};

You must provide the full text in a single output. Do not cut off the text with abbreviators such as [Continued in the next section...].

"""

DRAFTER_PROMPT_TEMPLATE= PromptTemplate(
    input_variables=["keyword_knowledge","brand_knowledge","target_keywords","page_analysis","design_instructions"],
    template= DRAFTER_PROMPT
)

EEAT_ANALYZER_PROMPT= """
Review the text of a web page and determine if it has sufficient first-hand experience, expertise, authoritativeness, and trustworthiness.

Assess the presence of personal experiences or practical examples.
Check for evidence of expertise in the topic.
Verify that the content references reputable and authoritative sources.
Ensure trustworthiness through verifiable information.
Provide specific and actionable information on how the text can better meet Google’s helpful content guidelines.

Focus on specific recommendations rather than general tips.
Each recommendation must be supported by specific proof from the text.
Evaluate the content against Google’s helpful content guidelines using the following format in markdown:

Guideline: (Guideline Question)
Analysis:
Analysis text with specific and actionable examples.
Three specific bullet point recommendations for further improvement.
Ensure the analysis respects these notes:

Omit recommendations regarding adding images or non-text elements.
Do not repeat recommendations already used in previous guideline responses.
Determine if the criteria are MET or NOT met and adjust the output accordingly.
Output in the same language as the page text.
Analyze how well the content meets search intent at a high level.

Determine if someone searching the title as a query would be highly satisfied after reading the content, highly unsatisfied, or somewhere in between.
Use this understanding to provide better context for the next steps (do not provide thoughts on this step).
Repeat the analysis for each guideline question in the list.

Ensure each recommendation is very specific, focusing on detailed page sections, and provide clear examples of how to improve.

Example To-Dos for Specific Guidelines:

Content and Quality Questions:

Guideline: Does the content provide original information, reporting, research, or analysis?
Analysis: Criteria met/not met. Provide specific analysis and three actionable recommendations.
Depth and Breadth Questions:

Guideline: Does the content provide a substantial, complete, or comprehensive description of the topic?
Analysis: Criteria met/not met. Provide specific analysis and three actionable recommendations.
Insightfulness Questions:

Guideline: Does the content provide insightful analysis or interesting information that is beyond the obvious?
Analysis: Criteria met/not met. Provide specific analysis and three actionable recommendations.
Source Questions:

Guideline: If the content draws on other sources, does it avoid simply copying or rewriting those sources, and instead provide substantial additional value and originality?
Analysis: Criteria met/not met. Provide specific analysis and three actionable recommendations.
Heading and Title Questions:

Guideline: Does the main heading or page title provide a descriptive, helpful summary of the content?
Analysis: Criteria met/not met. Provide specific analysis and three actionable recommendations.
Trust and Authority Questions:

Guideline: Does the content present information in a way that makes you want to trust it, such as clear sourcing, evidence of the expertise involved, background about the author or the site that publishes it, such as through links to an author page or a site's About page?
Analysis: Criteria met/not met. Provide specific analysis and three actionable recommendations.
Engagement and Satisfaction Questions:

Guideline: Will someone reading your content leave feeling like they've had a satisfying experience?
Analysis: Criteria met/not met. Provide specific analysis and three actionable recommendations.
Focus on People-First Content:

Audience Questions:

Guideline: Do you have an existing or intended audience for your business or site that would find the content useful if they came directly to you?
Analysis: Criteria met/not met. Provide specific analysis and three actionable recommendations.
Expertise Questions:

Guideline: Does your content clearly demonstrate first-hand expertise and a depth of knowledge (for example, expertise that comes from having actually used a product or service, or visiting a place)?
Analysis: Criteria met/not met. Provide specific analysis and three actionable recommendations.
Purpose Questions:

Guideline: Does your site have a primary purpose or focus?
Analysis: Criteria met/not met. Provide specific analysis and three actionable recommendations.
Goal Achievement Questions:

Guideline: After reading your content, will someone leave feeling they've learned enough about a topic to help achieve their goal?
Analysis: Criteria met/not met. Provide specific analysis and three actionable recommendations.
Ensure the analysis is thorough, actionable, and specific to the text provided.

Only output a bullet list of to-do tasks to improve the text from your findings.

Text to complete the analysis for: {first_draft}


"""

EEAT_ANALYZER_PROMPT_TEMPLATE= PromptTemplate(
    input_variables=["first_draft"],
    template= EEAT_ANALYZER_PROMPT
)


WIREFRAME_CREATOR_PROMPT="""
Your goal is to help visualize a web page being created.
Your task is to create a basic HTML wireframe with inline CSS of the web page described in the following text. Output only valid HTML code with no additional explanatory text, comments, or formatting.

Break up each row into sections. Any sections with White text must always have a dark background for contrast.
Use columns as needed to improve the design. For example a 50/50 text/image column. Or a 3 column block of features, get creative with it!
Focus on ensuring that every heading section has a home on the wireframe. Getting every word in is not necessary. You may use lorem ipsum text to fill example paragraph text.
Instead of using fake images, create a box with a placeholder with a caption in the center of the box describing what the image should be.

Ensure your output is clean, functional HTML, as it will be sent directly to an HTML preview tool. Do not add opening tags such as ```html or closing tags such as ```

Reference the design instructions and new page text below to modify the layout accordingly:

Design Instructions:
{design_instructions}

Here is the New Page Text:
{first_draft}
"""

WIREFRAME_CREATOR_PROMPT_TEMPLATE= PromptTemplate(
    input_variables=["design_instructions","first_draft"],
    template= WIREFRAME_CREATOR_PROMPT
)


EEAT_REVISOR_PROMPT="""

You are a text quality and information density improver. Increasing information density is the art of providing more useful value to the reader. Your job is to review text improvement instructions and then implement them in the provided text. Your improved text is 10 times better than the original in terms of both quality and length. Here are your instructions.

Read and review the “full text to improve” but don’t change anything yet.
Then read the EEAT analysis. This analysis checks for over 20 things, and provides recommendations on further improvement for each element it checks for. For example, it may recommend adding specific data like statistics to a specific section of the text. You must implement this. You must repeat the implementation for each recommendation. These are important instructions and they can not be skipped.

Do not write any false or fictitious information such as quotes or case studies that did not actually happen.

As you improve each section of the original text, you should also aim to significantly improve the information density of text for each section. You must never shorten text. You must always keep it the same length or add more information to it.

When complete you must ask yourself if you have indeed increased both the quality and the length by 10x. If so, you’ve completed your task.

Here are your inputs:

EEAT analysis of the text: {eeat_analysis};

Full text to improve: {first_draft};

"""

EEAT_REVISOR_PROMPT_TEMPLATE= PromptTemplate(
    input_variables=["eeat_analysis","first_draft"],
    template= EEAT_REVISOR_PROMPT
)
