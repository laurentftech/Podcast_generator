from setuptools import setup

# Lit le contenu du fichier README pour la description longue
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='Podcast Generator',
    author='Laurent FRANCOISE',
    author_email='laurent.f.tech@icloud.com',
    description='Une application de bureau pour créer des podcasts audio à partir de scripts en utilisant l\'API Gemini.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/laurentftech/Podcast_generator',
    license='MIT',
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    py_modules=['gui', 'generate_podcast'], # Spécifie les modules principaux
    install_requires=[
        'google-genai',
        'python-dotenv',
        'keyring',
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
