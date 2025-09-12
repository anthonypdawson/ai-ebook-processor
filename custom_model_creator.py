"""
Custom Ollama Model Creator

This creates a custom Ollama model with knowledge about your processed books
by embedding summaries into the system prompt.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict
import subprocess

logger = logging.getLogger(__name__)


class CustomModelCreator:
    """Create custom Ollama models with ebook knowledge"""
    
    def __init__(self, base_model: str = "llama2"):
        self.base_model = base_model
    
    def create_knowledge_model(self, 
                             processed_results: List[Dict], 
                             model_name: str = "my-book-expert") -> str:
        """
        Create a custom Ollama model with book knowledge embedded in system prompt
        
        Args:
            processed_results: List of processed ebook results
            model_name: Name for the new custom model
            
        Returns:
            Path to the created Modelfile
        """
        
        # Extract key information from processed books
        book_knowledge = self._extract_book_knowledge(processed_results)
        
        # Create system prompt with book knowledge
        system_prompt = self._create_system_prompt(book_knowledge)
        
        # Create Modelfile
        modelfile_content = f"""FROM {self.base_model}

SYSTEM \"\"\"You are an expert on the user's personal book collection. You have knowledge of the following books and their content:

{system_prompt}

When answering questions, draw from this knowledge when relevant. Be specific about which books you're referencing.\"\"\"

PARAMETER temperature 0.7
PARAMETER top_p 0.9
"""
        
        # Save Modelfile
        modelfile_path = Path(f"Modelfile.{model_name}")
        with open(modelfile_path, 'w', encoding='utf-8') as f:
            f.write(modelfile_content)
        
        # Instructions for creating the model
        instructions = f"""
Custom model configuration created: {modelfile_path}

To create your custom model, run:
    ollama create {model_name} -f {modelfile_path}

Then use it with:
    ollama run {model_name}
    
Or update your config to use model: "{model_name}"
"""
        
        print(instructions)
        logger.info(f"Custom model configuration created: {modelfile_path}")
        
        return str(modelfile_path)
    
    def auto_create_model(self, modelfile_path: str, model_name: str) -> bool:
        """
        Automatically create the Ollama model using subprocess
        
        Args:
            modelfile_path: Path to the Modelfile
            model_name: Name for the new model
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = ["ollama", "create", model_name, "-f", modelfile_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✓ Successfully created model: {model_name}")
                print(f"You can now use: ollama run {model_name}")
                return True
            else:
                print(f"Error creating model: {result.stderr}")
                return False
                
        except FileNotFoundError:
            print("Ollama command not found. Make sure Ollama is installed and in PATH.")
            return False
        except Exception as e:
            print(f"Error creating model: {e}")
            return False
    
    def _extract_book_knowledge(self, results: List[Dict]) -> List[Dict]:
        """Extract key knowledge from processed ebook results"""
        knowledge = []
        
        for result in results:
            if 'error' in result:
                continue
                
            metadata = result.get('metadata', {})
            content = result.get('combined_result', '')
            book_summary = result.get('book_summary', '')
            
            # Create condensed knowledge entry
            book_info = {
                'title': metadata.get('title', 'Unknown'),
                'author': metadata.get('author', 'Unknown'),
                'format': metadata.get('format', 'Unknown'),
                'summary': book_summary if book_summary else content[:2000] + "...",
                'key_insights': self._extract_key_points(content)
            }
            
            knowledge.append(book_info)
        
        return knowledge
    
    def _extract_key_points(self, content: str) -> str:
        """Extract key points from processed content"""
        # Simple extraction - look for common summary patterns
        sentences = content.split('. ')
        key_sentences = []
        
        key_phrases = [
            'key theme', 'main idea', 'important concept', 'central argument',
            'significant finding', 'crucial point', 'major insight', 'essential'
        ]
        
        for sentence in sentences:
            if any(phrase in sentence.lower() for phrase in key_phrases):
                key_sentences.append(sentence.strip())
                if len(key_sentences) >= 3:  # Limit to 3 key points
                    break
        
        return '. '.join(key_sentences) if key_sentences else content[:500]
    
    def _create_system_prompt(self, book_knowledge: List[Dict]) -> str:
        """Create system prompt with book knowledge"""
        prompt_parts = []
        
        for book in book_knowledge:
            book_section = f"""
BOOK: "{book['title']}" by {book['author']}
FORMAT: {book['format']}
SUMMARY: {book['summary'][:1000]}
KEY INSIGHTS: {book['key_insights']}
"""
            prompt_parts.append(book_section)
        
        return "\n".join(prompt_parts)


# Integration with main app
def create_book_expert_model(processed_results: List[Dict], 
                           model_name: str = "my-book-expert",
                           auto_create: bool = True) -> str:
    """
    Convenience function to create a custom model from processed results
    
    Args:
        processed_results: Results from processing ebooks
        model_name: Name for the custom model
        auto_create: Whether to automatically create the model with Ollama
        
    Returns:
        Path to the Modelfile or status message
    """
    creator = CustomModelCreator()
    modelfile_path = creator.create_knowledge_model(processed_results, model_name)
    
    if auto_create:
        success = creator.auto_create_model(modelfile_path, model_name)
        if success:
            return f"✓ Custom model '{model_name}' created successfully!"
        else:
            return f"Modelfile created at {modelfile_path}. Create manually with: ollama create {model_name} -f {modelfile_path}"
    
    return modelfile_path


# Example usage
if __name__ == "__main__":
    print("Custom Ollama Model Creator")
    print("Creates models with embedded knowledge of your books")
    print("\nThis embeds book summaries into the model's system prompt,")
    print("giving it 'knowledge' of your book collection.")