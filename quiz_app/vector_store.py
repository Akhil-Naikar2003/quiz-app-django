# import os
# import json
# import random
# from langchain_community.vectorstores import FAISS
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain_community.embeddings import HuggingFaceEmbeddings
# from langchain_community.document_loaders import PyPDFLoader
# from langchain.chains import RetrievalQA
# from langchain_groq import ChatGroq
# from dotenv import load_dotenv
# import re

# # Load environment variables
# load_dotenv()

# class PDFProcessor:
#     def __init__(self):
#         # Initialize embeddings
#         self.embeddings = HuggingFaceEmbeddings(
#             model_name="all-MiniLM-L6-v2",
#             model_kwargs={'device': 'cpu'}
#         )

#         # Initialize text splitter
#         self.text_splitter = RecursiveCharacterTextSplitter(
#             chunk_size=1000,
#             chunk_overlap=200,
#             length_function=len,
#         )

#         # Initialize LLM
#         groq_api_key = os.getenv("GROQ_API_KEY")
#         if not groq_api_key:
#             raise ValueError("GROQ_API_KEY not found in environment variables")

#         self.llm = ChatGroq(
#             model="gemma2-9b-it",
#             temperature=0.7
#         )

#     def process_pdf(self, pdf_path):
#         """Process PDF and create vector store"""
#         # Load PDF
#         loader = PyPDFLoader(pdf_path)
#         pages = loader.load()
        
#         # Split into chunks
#         texts = self.text_splitter.split_documents(pages)
        
#         # Create vector store
#         vector_store = FAISS.from_documents(texts, self.embeddings)
        
#         return vector_store

#     # def generate_questions(self, vector_store, difficulty, num_questions, quiz_id=None):
#     #     """Generate diverse questions using chunks sampled across the entire PDF"""
        
#     #     # Get all chunks from FAISS vector store
#     #     all_chunks = list(vector_store.docstore._dict.values())

#     #     if not all_chunks:
#     #         print("No chunks found in vector store.")
#     #         return []

#     #     # Check existing questions from DB to avoid duplicates
#     #     existing_questions = set()
#     #     if quiz_id:
#     #         existing_questions = self.check_existing_questions(quiz_id)

#     #     questions = []
#     #     used_questions = set()

#     #     attempts = 0
#     #     max_attempts = num_questions * 5
#     #     consecutive_errors = 0
#     #     max_consecutive_errors = 10

#     #     while len(questions) < num_questions and attempts < max_attempts:
#     #         attempts += 1

#     #         # Randomly sample 3 chunks from across the PDF
#     #         sampled_chunks = random.sample(all_chunks, min(3, len(all_chunks)))
#     #         context = "\n".join([chunk.page_content for chunk in sampled_chunks])

#     #         # Prompt with context
#     #         prompt = f"""
#     #         Context:
#     #         {context}

#     #         Based on the above context, generate a {difficulty} difficulty multiple choice question.
#     #         The question should test understanding, application, or analysis.
#     #         Format your response as valid JSON:
#     #         {{
#     #             "mcq": "your question?",
#     #             "options": {{
#     #                 "A": "Option A",
#     #                 "B": "Option B",
#     #                 "C": "Option C",
#     #                 "D": "Option D"
#     #             }},
#     #             "correct": "A/B/C/D"
#     #         }}
#     #         """

#     #         try:
#     #             response = self.llm.invoke(prompt)
#     #             json_str = response.content.strip().replace('```json', '').replace('```', '')
#     #             json_str = re.sub(r',\s*}', '}', json_str)
#     #             json_str = re.sub(r',\s*]', ']', json_str)

#     #             # Try JSON load
#     #             try:
#     #                 question = json.loads(json_str)
#     #             except json.JSONDecodeError:
#     #                 try:
#     #                     question = eval(json_str)
#     #                 except Exception as e:
#     #                     print(f"Eval parse failed: {e}")
#     #                     consecutive_errors += 1
#     #                     continue

#     #             # Reset error counter on success
#     #             consecutive_errors = 0

#     #             # Validate structure
#     #             if not self._is_valid_question(question):
#     #                 print("Invalid question format:", question)
#     #                 continue

#     #             # Check for duplicates
#     #             question_id = self._create_question_id(question)
#     #             if question_id not in used_questions and question_id not in existing_questions:
#     #                 used_questions.add(question_id)
#     #                 questions.append(question)
#     #                 print(f"Generated unique question {len(questions)}/{num_questions}")
#     #             else:
#     #                 print(f"Duplicate detected. Attempt {attempts}")

#     #         except Exception as e:
#     #             print(f"Exception during generation: {e}")
#     #             consecutive_errors += 1
#     #             if consecutive_errors >= max_consecutive_errors:
#     #                 print("Too many consecutive errors. Stopping.")
#     #                 break

#     #     print(f"Final questions generated: {len(questions)} / {num_questions}")
#     #     return questions


#     def generate_questions(self, vector_store, difficulty, num_questions, quiz_id=None):
#         """Generate diverse questions using vector store"""
#         # Create retrieval chain with more diverse retrieval
#         qa_chain = RetrievalQA.from_chain_type(
#             llm=self.llm,
#             chain_type="stuff",
#             retriever=vector_store.as_retriever(
#                 search_kwargs={"k": 5}  # Retrieve more chunks for diversity
#             )
#         )

#         # Check for existing questions if quiz_id is provided
#         existing_questions = set()
#         if quiz_id:
#             existing_questions = self.check_existing_questions(quiz_id)

#         # Different question types and prompts for diversity
#         question_types = [
#             "definition",
#             "application",
#             "analysis",
#             "comparison",
#             "evaluation",
#             "synthesis",
#             "comprehension",
#             "recall"
#         ]
        
#         question_templates = [
#             "What is the definition of {concept}?",
#             "How would you apply {concept} in a real-world scenario?",
#             "Analyze the relationship between {concept1} and {concept2}.",
#             "Compare and contrast {concept1} with {concept2}.",
#             "Evaluate the effectiveness of {concept}.",
#             "What are the key components of {concept}?",
#             "Explain the process of {concept}.",
#             "What are the main characteristics of {concept}?"
#         ]

#         questions = []
#         used_questions = set()  # Track used questions to avoid duplicates

#         attempts = 0
#         max_attempts = num_questions * 5  # Increased from 3 to 5 for more attempts
#         consecutive_errors = 0
#         max_consecutive_errors = 10  # Allow more consecutive errors

#         while len(questions) < num_questions and attempts < max_attempts:
#             attempts += 1

#             # Randomly select question type and template
#             question_type = random.choice(question_types)
#             template = random.choice(question_templates)
            
#             # Create diverse prompts
#             prompts = [
#                 f"""
#                 Based on the provided context, create a {difficulty} difficulty multiple choice question.
#                 Question type: {question_type}
#                 Focus on testing understanding and application of key concepts.
#                 Ensure the question is unique and different from typical questions.
                
#                 Format the response as valid JSON:
#                 {{
#                     "mcq": "your question here",
#                     "options": {{
#                         "A": "option A",
#                         "B": "option B", 
#                         "C": "option C",
#                         "D": "option D"
#                     }},
#                     "correct": "A/B/C/D"
#                 }}
#                 """,
                
#                 f"""
#                 Generate a {difficulty} level multiple choice question from the context.
#                 Make it a {question_type} type question that requires critical thinking.
#                 The question should be specific and test deep understanding.
                
#                 Return only valid JSON:
#                 {{
#                     "mcq": "question text",
#                     "options": {{
#                         "A": "first option",
#                         "B": "second option",
#                         "C": "third option", 
#                         "D": "fourth option"
#                     }},
#                     "correct": "correct letter"
#                 }}
#                 """,
                
#                 f"""
#                 Create a challenging {difficulty} multiple choice question.
#                 Question focus: {question_type}
#                 Template: {template}
#                 Make sure all options are plausible but only one is correct.
                
#                 JSON format:
#                 {{
#                     "mcq": "question",
#                     "options": {{
#                         "A": "option A",
#                         "B": "option B",
#                         "C": "option C",
#                         "D": "option D"
#                     }},
#                     "correct": "A/B/C/D"
#                 }}
#                 """
#             ]
            
#             # Use different prompts for variety
#             prompt = random.choice(prompts)
            
#             try:
#                 # Get response
#                 response = qa_chain.invoke(prompt)
#                 json_str = response['result'].replace('```json', '').replace('```', '').strip()
                
#                 # Clean the JSON string more thoroughly
#                 json_str = json_str.replace('```json', '').replace('```', '').strip()
                
#                 # Try to parse JSON with better error handling
#                 question = None
#                 try:
#                     question = json.loads(json_str)
#                 except json.JSONDecodeError as e:
#                     # Try to fix common JSON issues
#                     try:
#                         # Remove any trailing commas
#                         json_str = re.sub(r',\s*}', '}', json_str)
#                         json_str = re.sub(r',\s*]', ']', json_str)
#                         question = json.loads(json_str)
#                     except:
#                         # Fallback to eval if json.loads fails
#                         try:
#                             question = eval(json_str)
#                         except:
#                             print(f"Failed to parse JSON: {str(e)}")
#                             consecutive_errors += 1
#                             continue
                
#                 # Reset consecutive errors on success
#                 consecutive_errors = 0
                
#                 # Validate question structure
#                 if not self._is_valid_question(question):
#                     print(f"Invalid question structure: {question}")
#                     continue
                
#                 # Create a unique identifier for the question
#                 question_id = self._create_question_id(question)
                
#                 # Check for duplicates (both in current generation and existing questions)
#                 if question_id not in used_questions and question_id not in existing_questions:
#                     used_questions.add(question_id)
#                     questions.append(question)
#                     print(f"Generated unique question {len(questions)}/{num_questions}")
#                 else:
#                     print(f"Duplicate question detected, retrying... (attempt {attempts})")
                    
#             except Exception as e:
#                 print(f"Error processing question: {str(e)}")
#                 consecutive_errors += 1
#                 continue

#         print(f"Generated {len(questions)} unique questions after {attempts} attempts")
        
#         # If we couldn't generate enough questions, try with less strict duplicate detection
#         if len(questions) < num_questions:
#             print(f"Could not generate {num_questions} questions. Generated {len(questions)} questions.")
#             print("This might be due to limited content in the PDF or strict duplicate detection.")
        
#         return questions








#     def _is_valid_question(self, question):
#         """Validate question structure"""
#         required_keys = ['mcq', 'options', 'correct']
#         if not all(key in question for key in required_keys):
#             return False
        
#         if not question['mcq'] or len(question['mcq'].strip()) < 10:
#             return False
            
#         if not isinstance(question['options'], dict) or len(question['options']) != 4:
#             return False
            
#         if question['correct'] not in ['A', 'B', 'C', 'D']:
#             return False
            
#         return True

#     def _create_question_id(self, question):
#         """Create a unique identifier for a question to detect duplicates"""
#         # Create a simplified version of the question for comparison
#         question_text = question['mcq'].lower().strip()
#         # Remove common words and punctuation
#         question_text = re.sub(r'[^\w\s]', '', question_text)
#         words = question_text.split()
#         # Use first 3 significant words (reduced from 5 to be less strict)
#         significant_words = [w for w in words if len(w) > 3][:3]
#         return ' '.join(significant_words)

#     def check_existing_questions(self, quiz_id):
#         """Check for existing questions in the database to avoid duplicates"""
#         from django.db import connection
#         from quiz_app.models import Question

#         try:
#             # Get existing questions for this quiz
#             existing_questions = Question.objects.filter(quiz_id=quiz_id).values_list('text', flat=True)
            
#             # Create simplified versions for comparison
#             existing_simplified = set()
#             for q_text in existing_questions:
#                 simplified = self._create_question_id({'mcq': q_text, 'options': {}, 'correct': ''})
#                 existing_simplified.add(simplified)
            
#             return existing_simplified
#         except Exception as e:
#             print(f"Error checking existing questions: {e}")
#             return set()

#     def save_vector_store(self, vector_store, store_path):
#         """Save vector store to disk"""
#         vector_store.save_local(store_path)

#     def load_vector_store(self, store_path):
#         """Load vector store from disk"""
#         return FAISS.load_local(store_path, self.embeddings,allow_dangerous_deserialization=True) 
import os
import json
import random
import re
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.chains import RetrievalQA
from langchain_groq import ChatGroq

load_dotenv()

class PDFProcessor:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")

        self.llm = ChatGroq(
            model="gemma2-9b-it",
            api_key=os.getenv("GROQ_API_KEY"), #change made
            temperature=0.7
        )

    def process_pdf(self, pdf_path):
        loader = PyPDFLoader(pdf_path)
        pages = loader.load()
        texts = self.text_splitter.split_documents(pages)
        return FAISS.from_documents(texts, self.embeddings)

    def save_vector_store(self, vector_store, store_path):
        vector_store.save_local(store_path)

    def load_vector_store(self, store_path):
        return FAISS.load_local(store_path, self.embeddings, allow_dangerous_deserialization=True)

    def summarize_chunkwise(self, vector_store, max_chunks=30, group_size=3):
        """Summarize the document by summarizing chunks in groups, then combining."""
        all_chunk_ids = list(vector_store.index_to_docstore_id.values())
        total_chunks = len(all_chunk_ids)
        chunk_summaries = []

        for i in range(0, min(max_chunks, total_chunks), group_size):
            chunk_indices = list(range(i, min(i + group_size, total_chunks)))
            chunk_ids = [all_chunk_ids[j] for j in chunk_indices]

            retriever = vector_store.as_retriever(search_kwargs={"k": len(chunk_ids), "doc_ids": chunk_ids})
            qa_chain = RetrievalQA.from_chain_type(llm=self.llm, chain_type="stuff", retriever=retriever)

            prompt = """
            Summarize the following content in 3–4 sentences.
            Focus on key technical concepts and explanations. Avoid lists or questions.
            """

            try:
                response = qa_chain.invoke(prompt)
                summary = response['result'].strip()
                if summary:
                    chunk_summaries.append(summary)
                    print(f"✅ Summarized chunk group {i // group_size + 1}")
            except Exception as e:
                print(f"⚠️ Error summarizing chunk group {i // group_size + 1}: {e}")

        final_prompt = f"""
        Combine the following summaries into a single, coherent summary:

        {' '.join(chunk_summaries)}

        Return a concise and readable overview of the full document.
        """

        try:
            final_response = self.llm.invoke(final_prompt)
            final_summary = final_response.content.strip()  # ✅ FIXED
            return final_summary
        except Exception as e:
            print(f"❌ Final summary combination failed: {e}")
            return "\n".join(chunk_summaries)

    def generate_questions(self, vector_store, difficulty, num_questions, quiz_id=None):
        """Efficiently generate multiple MCQs from a summary using fewer LLM calls."""
        summary = self.summarize_chunkwise(vector_store)
        print("\n📘 Summary used for question generation:\n", summary)

        used_questions = set()
        existing_questions = self.check_existing_questions(quiz_id) if quiz_id else set()
        questions = []
        max_batch = 5  # Questions per batch
        total_batches = (num_questions + max_batch - 1) // max_batch
        generated = 0

        for batch_index in range(total_batches):
            needed = min(max_batch, num_questions - generated)

            prompt = f"""
            Based on the following summary, generate {needed} unique {difficulty} level multiple choice questions.

            Summary:
            {summary}

            Format: Return a **JSON array** of {needed} questions. Each item must follow this format:
            {{
            "mcq": "Your question here?",
            "options": {{
                "A": "Option A",
                "B": "Option B",
                "C": "Option C",
                "D": "Option D"
            }},
            "correct": "A/B/C/D"
            }}

            Do not include explanations or markdown. Just return the raw JSON array.
            """

            try:
                response = self.llm.invoke(prompt)
                raw = response.content.strip().replace("```json", "").replace("```", "").strip()
                try:
                    items = json.loads(raw)
                except json.JSONDecodeError:
                    try:
                        items = eval(raw)
                    except:
                        print("⚠️ Failed to parse response even with eval fallback.")
                        continue

                if not isinstance(items, list):
                    print("⚠️ LLM did not return a JSON list.")
                    continue

                for q in items:
                    if not self._is_valid_question(q):
                        print("⚠️ Skipped invalid question:", q)
                        continue

                    qid = self._create_question_id(q)
                    if qid in used_questions or qid in existing_questions:
                        print("⚠️ Skipped duplicate question:", q['mcq'])
                        continue

                    used_questions.add(qid)
                    questions.append(q)
                    generated += 1
                    print(f"✅ Question {generated}/{num_questions} added.")

                    if generated >= num_questions:
                        break

            except Exception as e:
                print(f"❌ Exception while generating batch {batch_index + 1}: {e}")

        print(f"🎯 Finished generating {len(questions)} out of {num_questions} requested.")
        return questions


    def _safe_parse_json(self, text):
        try:
            return json.loads(text)
        except:
            try:
                return eval(text)
            except:
                return {}

    def _is_valid_question(self, question):
        if not all(k in question for k in ['mcq', 'options', 'correct']):
            return False
        if not question['mcq'] or len(question['mcq']) < 10:
            return False
        if not isinstance(question['options'], dict) or len(question['options']) != 4:
            return False
        if question['correct'] not in ['A', 'B', 'C', 'D']:
            return False
        return True

    def _create_question_id(self, question):
        text = question['mcq'].lower().strip()
        text = re.sub(r'[^\w\s]', '', text)
        words = text.split()
        sig_words = [w for w in words if len(w) > 3][:3]
        return ' '.join(sig_words)

    def _simplify_text(self, text):
        text = text.lower().strip()
        text = re.sub(r'[^\w\s]', '', text)
        words = text.split()
        sig_words = [w for w in words if len(w) > 3][:3]
        return ' '.join(sig_words)

    def check_existing_questions(self, quiz_id):
        from quiz_app.models import Question
        try:
            existing_texts = Question.objects.filter(quiz_id=quiz_id).values_list('text', flat=True)
            return {self._simplify_text(q) for q in existing_texts}
        except Exception as e:
            print(f"DB Error: {e}")
            return set()
