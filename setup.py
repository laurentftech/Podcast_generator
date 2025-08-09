from setuptools import setup

# Lit le contenu du fichier README pour la description longue
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='Podcast_creator',
    version='1.0.0',
    author='Laurent FRANCOISE',
    author_email='lfrancoise@gmail.com',
    description='Une application de bureau pour générer des podcasts audio à partir de scripts en utilisant l\'API Gemini.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://gitea.gandulf78.synology.me/laurent/Podcast_creator',
    license='MIT',
    py_modules=['gui', 'generate_podcast'], # Spécifie les modules principaux
    install_requires=[
        'google-genai',
        'python-dotenv',
        'simpleaudio',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Environment :: Win32 (MS Windows)",
        "Environment :: MacOS X",
        "Framework :: Tkinter",
    ],
    python_requires='>=3.9',
)
