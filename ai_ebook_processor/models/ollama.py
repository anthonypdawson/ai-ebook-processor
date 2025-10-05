"""
Ollama Integration Module

This module provides functionality to connect to and interact with Ollama models
for processing text content from ebooks.
"""

import asyncio
from ai_ebook_processor.utils.logger import get_logger
from typing import Dict, List, Optional, Generator, Any
import json
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from pathlib import Path
import time

import ollama
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)


class OllamaProcessor:
    """Main class for processing text through Ollama models"""
    
    def __init__(self, 
                 model_name: str = "llama2", 
                 host: str = "http://localhost:11434",
                 temperature: float = 0.7,
                 max_tokens: Optional[int] = None):
        """
        Initialize Ollama processor
        
        Args:
            model_name (str): Name of the Ollama model to use
            host (str): Ollama server host URL
            temperature (float): Temperature for text generation
            max_tokens (Optional[int]): Maximum tokens per request
        """
        self.model_name = model_name
        self.host = host
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = ollama.Client(host=host)
        
        # Verify model exists
        self._verify_model()
    
    def _verify_model(self) -> None:
        """Verify that the specified model is available"""
        try:
            models = self.client.list()
            available_models = [model.model for model in models.models]
            
            if self.model_name not in available_models:
                logger.warning(f"Model '{self.model_name}' not found in available models: {available_models}")
                logger.info(f"You can download the model by running: ollama pull {self.model_name}")
                raise ValueError(f"Model '{self.model_name}' not available. Available models: {available_models}")
            
            logger.info(f"Successfully connected to Ollama model: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Error connecting to Ollama: {e}")
            logger.info("Make sure Ollama is running (ollama serve) and the model is pulled")
            raise
    
    def list_available_models(self) -> List[Dict]:
        """List all available models"""
        try:
            models = self.client.list()
            return [{'name': model.model} for model in models.models]
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []
    
    def process_text(self, 
                     text: str, 
                     prompt_template: str = None, 
                     system_prompt: str = None) -> str:
        """
        Process a single text chunk through Ollama
        
        Args:
            text (str): Text content to process
            prompt_template (str): Template for the prompt (should contain {text} placeholder)
            system_prompt (str): System prompt to set context
            
        Returns:
            str: Processed text response from the model
        """
        if not text.strip():
            return ""
        
        # Default prompt template
        if prompt_template is None:
            prompt_template = "Please analyze and summarize the following text:\n\n{text}"
        
        # Format the prompt
        formatted_prompt = prompt_template.format(text=text)
        
        try:
            response = self.client.chat(
                model=self.model_name,
                messages=[
                    {'role': 'system', 'content': system_prompt or 'You are a helpful assistant analyzing text content.'},
                    {'role': 'user', 'content': formatted_prompt}
                ],
                options={
                    'temperature': self.temperature,
                    'num_predict': self.max_tokens
                } if self.max_tokens else {'temperature': self.temperature}
            )
            
            return response['message']['content']
            
        except Exception as e:
            logger.error(f"Error processing text with Ollama: {e}")
            raise
    
    def process_text_streaming(self, 
                              text: str, 
                              prompt_template: str = None, 
                              system_prompt: str = None) -> Generator[str, None, None]:
        """
        Process text with streaming response
        
        Args:
            text (str): Text content to process
            prompt_template (str): Template for the prompt
            system_prompt (str): System prompt to set context
            
        Yields:
            str: Streaming response chunks from the model
        """
        if not text.strip():
            return
        
        if prompt_template is None:
            prompt_template = "Please analyze and summarize the following text:\n\n{text}"
        
        formatted_prompt = prompt_template.format(text=text)
        
        try:
            stream = self.client.chat(
                model=self.model_name,
                messages=[
                    {'role': 'system', 'content': system_prompt or 'You are a helpful assistant analyzing text content.'},
                    {'role': 'user', 'content': formatted_prompt}
                ],
                stream=True,
                options={
                    'temperature': self.temperature,
                    'num_predict': self.max_tokens
                } if self.max_tokens else {'temperature': self.temperature}
            )
            
            for chunk in stream:
                if chunk['message']['content']:
                    yield chunk['message']['content']
                    
        except Exception as e:
            logger.error(f"Error in streaming processing: {e}")
            raise
    
    def process_chunks(self, 
                       text_chunks: List[str], 
                       prompt_template: str = None,
                       system_prompt: str = None,
                       progress_bar: bool = True) -> List[Dict]:
        """
        Process multiple text chunks
        
        Args:
            text_chunks (List[str]): List of text chunks to process
            prompt_template (str): Template for the prompt
            system_prompt (str): System prompt
            progress_bar (bool): Whether to show progress bar
            
        Returns:
            List[Dict]: List of results with chunk info and responses
        """
        results = []
        
        iterator = enumerate(text_chunks)
        if progress_bar:
            iterator = tqdm(iterator, total=len(text_chunks), desc="Processing chunks")
        
        for i, chunk in iterator:
            try:
                start_time = time.time()
                response = self.process_text(chunk, prompt_template, system_prompt)
                processing_time = time.time() - start_time
                
                results.append({
                    'chunk_index': i,
                    'chunk_length': len(chunk),
                    'response': response,
                    'response_length': len(response),
                    'processing_time': processing_time,
                    'success': True
                })
                
            except Exception as e:
                logger.error(f"Error processing chunk {i}: {e}")
                results.append({
                    'chunk_index': i,
                    'chunk_length': len(chunk),
                    'response': "",
                    'error': str(e),
                    'success': False
                })
        
        return results
    
    def process_chunks_parallel(self, 
                               text_chunks: List[str], 
                               prompt_template: str = None,
                               system_prompt: str = None,
                               max_workers: int = 4,
                               progress_bar: bool = True) -> List[Dict]:
        """
        Process multiple text chunks in parallel for much faster processing
        
        Args:
            text_chunks (List[str]): List of text chunks to process
            prompt_template (str): Template for the prompt
            system_prompt (str): System prompt
            max_workers (int): Number of parallel threads (default: 4)
            progress_bar (bool): Whether to show progress bar
            
        Returns:
            List[Dict]: List of results with chunk info and responses
        """
        results = [None] * len(text_chunks)  # Pre-allocate results list
        
        def process_single_chunk(i: int, chunk: str) -> Dict:
            """Process a single chunk and return result with index"""
            try:
                start_time = time.time()
                response = self.process_text(chunk, prompt_template, system_prompt)
                processing_time = time.time() - start_time
                
                return {
                    'chunk_index': i,
                    'chunk_length': len(chunk),
                    'response': response,
                    'response_length': len(response),
                    'processing_time': processing_time,
                    'success': True
                }
                
            except Exception as e:
                logger.error(f"Error processing chunk {i}: {e}")
                return {
                    'chunk_index': i,
                    'chunk_length': len(chunk),
                    'response': "",
                    'error': str(e),
                    'success': False
                }
        
        # Process chunks in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_index = {
                executor.submit(process_single_chunk, i, chunk): i 
                for i, chunk in enumerate(text_chunks)
            }
            
            # Collect results with progress bar
            if progress_bar:
                from tqdm import tqdm
                futures = tqdm(as_completed(future_to_index), 
                              total=len(text_chunks), 
                              desc=f"Processing chunks (parallel x{max_workers})")
            else:
                futures = as_completed(future_to_index)
            
            for future in futures:
                try:
                    result = future.result()
                    results[result['chunk_index']] = result
                except Exception as e:
                    index = future_to_index[future]
                    logger.error(f"Future error for chunk {index}: {e}")
                    results[index] = {
                        'chunk_index': index,
                        'chunk_length': len(text_chunks[index]) if index < len(text_chunks) else 0,
                        'response': "",
                        'error': str(e),
                        'success': False
                    }
        
        return results
    
    def create_book_summary(self, text: str, metadata: Dict) -> str:
        """
        Create a comprehensive summary of a book
        
        Args:
            text (str): Full text content of the book
            metadata (Dict): Book metadata
            
        Returns:
            str: Comprehensive book summary
        """
        summary_prompt = f"""Please create a comprehensive summary of this book:

Title: {metadata.get('title', 'Unknown')}
Author: {metadata.get('author', 'Unknown')}
Format: {metadata.get('format', 'Unknown')}

Please provide:
1. A brief overview of the book's main themes and content
2. Key concepts, ideas, or plot points
3. The author's main arguments or narrative structure
4. Notable quotes or important passages (if any)
5. Overall assessment and significance

Book content:
{text[:10000]}...{"[Content truncated]" if len(text) > 10000 else ""}
"""
        
        try:
            return self.process_text(text, summary_prompt, 
                                   "You are a literary analyst providing comprehensive book summaries.")
        except Exception as e:
            logger.error(f"Error creating book summary: {e}")
            return f"Error creating summary: {e}"
    
    def extract_key_insights(self, text: str) -> str:
        """
        Extract key insights from text content
        
        Args:
            text (str): Text content to analyze
            
        Returns:
            str: Key insights and important points
        """
        insights_prompt = """Please extract the most important insights, key points, and valuable information from this text. Focus on:
        
        1. Main ideas and concepts
        2. Important facts or data
        3. Actionable insights
        4. Notable quotes or statements
        5. Key takeaways
        
        Text content:
        {text}"""
        
        try:
            return self.process_text(text, insights_prompt,
                                   "You are an expert analyst extracting key insights from text.")
        except Exception as e:
            logger.error(f"Error extracting insights: {e}")
            return f"Error extracting insights: {e}"
    
    def create_questions_and_answers(self, text: str) -> str:
        """
        Generate questions and answers based on the text content
        
        Args:
            text (str): Text content to analyze
            
        Returns:
            str: Generated Q&A pairs
        """
        qa_prompt = """Based on the following text, please create a set of important questions and their answers that would help someone understand the key concepts and information. Format as Q: [Question] A: [Answer]

        Text content:
        {text}"""
        
        try:
            return self.process_text(text, qa_prompt,
                                   "You are an educational assistant creating study questions and answers.")
        except Exception as e:
            logger.error(f"Error creating Q&A: {e}")
            return f"Error creating Q&A: {e}"
    
    def save_results(self, results: List[Dict], output_path: str) -> None:
        """
        Save processing results to a file
        
        Args:
            results (List[Dict]): Processing results
            output_path (str): Path to save results
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save as JSON for structured data
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Results saved to: {output_path}")
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            raise


# Predefined prompt templates
PROMPT_TEMPLATES = {
    'summary': 'Please provide a concise summary of the following text:\n\n{text}',
    'analysis': 'Please analyze the following text for key themes, concepts, and important information:\n\n{text}',
    'extraction': 'Please extract the most important facts, data, and insights from the following text:\n\n{text}',
    'questions': 'Based on the following text, create important study questions and provide answers:\n\n{text}',
    'critique': 'Please provide a thoughtful critique and analysis of the arguments presented in the following text:\n\n{text}',
    'simplify': 'Please explain the following text in simpler terms that would be easy to understand:\n\n{text}'
}

SYSTEM_PROMPTS = {
    'analyst': 'You are an expert text analyst who provides thorough and insightful analysis of written content.',
    'summarizer': 'You are a professional summarizer who creates concise, accurate summaries while preserving key information.',
    'educator': 'You are an educational assistant who helps create learning materials and study aids.',
    'critic': 'You are a thoughtful critic who provides balanced analysis and constructive feedback.',
    'simplifier': 'You are an expert at explaining complex concepts in simple, accessible language.'
}


# Example usage
if __name__ == "__main__":
    # Initialize processor
    processor = OllamaProcessor(model_name="llama2")
    
    # List available models
    models = processor.list_available_models()
    print("Available models:", [model['name'] for model in models])
    
    # Example text processing
    sample_text = "This is a sample text to demonstrate the Ollama integration."
    result = processor.process_text(sample_text, PROMPT_TEMPLATES['summary'])
    print("Summary:", result)