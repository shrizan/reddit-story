from video_pipeline.tools.tts_tool import TTSTool

tool = TTSTool()
result = tool._run(text="A fox lived in a forest and was very clever.", filename="test_audio.mp3")
print(f"Audio saved to: {result}")
