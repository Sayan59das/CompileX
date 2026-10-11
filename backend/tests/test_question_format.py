"""Quick test to verify question description format is correct."""
import asyncio, sys
sys.path.insert(0, '.')
from app.services.ai_generator import ai_generator
from app.models.models import DifficultyLevel

async def main():
    for diff in [DifficultyLevel.EASY, DifficultyLevel.MEDIUM, DifficultyLevel.HARD]:
        # use fallback directly
        result = ai_generator._fallback_question(diff, None, 3)
        desc = result['description']
        print(f"\n{'='*50}")
        print(f"  {diff.value.upper()}: {result['title']}")
        print(f"{'='*50}")
        print(desc[:500])
        
        # check all sections present
        for section in ['**Input Format**', '**Output Format**', '**Constraints**', '**Sample Input**', '**Sample Output**', '**Explanation**']:
            ok = section in desc
            print(f"  {'✓' if ok else '✗'} {section}")

asyncio.run(main())
