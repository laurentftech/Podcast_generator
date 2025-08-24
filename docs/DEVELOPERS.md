# Podcast Generator - Developer Guide

This document describes the steps to contribute, test, and prepare a new version of Podcast Generator.

⚠️ **Important**: The generation of executables (macOS, Windows, Linux) and their publication in the releases **is fully automated** through the GitHub Actions workflow `release.yml`.  
Only the repository owner (Laurent) can trigger this generation and officially publish a release.

---

## 📋 Prerequisites

- Python 3.9+ (3.11 or 3.12 recommended)
- Git
- FFmpeg installed and available in the PATH
- Access to the Git repository (push rights required to prepare a release)

---

## ⚙️ Setting up the development environment

```sh
# 1. Clone the repository
git clone https://github.com/laurentftech/Podcast_generator.git
cd Podcast_generator

# 2. Create and activate a Conda environment
conda create -n podcast_generator_dev python=3.11 -y
conda activate podcast_generator_dev

# 3. Install MFA with Conda
conda install -c conda-forge montreal-forced-aligner -y

# 4. Install other dependencies with pip
# The '-e' flag installs the project in "editable" mode for development.
pip install -e .[dev]

# 5. (Optional) Install textgrid if not covered by other dependencies
pip install textgrid

# 6. Run the application
python gui.py
```

---

## 📦 Building the Application Locally

The project uses a `Podcast Generator.spec` file to control the build process. This ensures consistency across all platforms and automates version injection.

### Build Steps

1.  **Cleanup (Recommended)**: Before building, it's a good practice to remove old build artifacts  to avoid caching issues.
    ```sh
    rm -rf build/ dist/ _version.py
    ```

2.  **Install Dependencies**: This step also generates the `_version.py` file needed for the build.
    ```sh
     pip install -e .[dev]
    ```

3.  **Run PyInstaller**: Use the `.spec` file to build the application.
    ```sh
    python -m PyInstaller "Podcast Generator.spec"
    ```

The final  executable will be located in the `dist` folder.

---

## 🚀 Preparing a new version

- **Final Tests**: Ensure all features are tested and functional.
- **Clean Working Directory**: Make sure your working directory is clean (`git status` should show no uncommitted changes).

Only Laurent can **publish an official release**, but anyone with write access can prepare the code.

### Step 2: Commit, Tag, and Push (**Laurent's Responsibility**)
```sh
git add .
git commit -m "Prepare version vX.Y.Z"
git tag -a vX.Y.Z -m "Version X.Y.Z"
git push origin main
git push origin vX.Y.Z
```

Once the `vX.Y.Z` tag is pushed, the GitHub Actions workflow `release.yml` will automatically build the application for all platforms, create a new GitHub Release, and upload all the .tar.gz archives.

No manual build is required.

---

## 🤝 Contributing

- Fork the repository  
- Create a branch:  
  ```sh
  git checkout -b feature/my-feature
  ```
- Develop and test your changes  
- Commit:  
  ```sh
  git commit -m "Added my feature"
  ```
- Push:  
  ```sh
  git push origin feature/my-feature
  ```
- Open a Pull Request

---

## 🛠 Development tips

- Follow the existing code structure and style
- Use explicit variable names
- Document new functions with docstrings
- Make commits clear and atomic
- Test compatibility on macOS, Windows, and Linux

---

## 📜 License

Contributions are accepted under the MIT license. See the [LICENSE](LICENSE) file for details.