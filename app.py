import gradio as gr
import subprocess
import os
import zipfile
import time
import re
from pathlib import Path


def process_video(video_file, project_dir, fps, progress=gr.Progress()):
    """
    Process video through the LichtFeld-Studio pipeline with minimal logging.
    Only shows errors, warnings, and major milestones to prevent system lag.

    Args:
        video_file: Path to uploaded video file
        project_dir: Name of the project directory
        fps: Frames per second for extraction

    Yields:
        status_message: String with processing status (streamed)
        zip_file_path: Path to downloadable zip file
    """
    log_buffer = []

    def strip_ansi_codes(text):
        """Remove ANSI color codes from text"""
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_escape.sub("", text)

    def add_log(msg):
        """Add a message to the log buffer and return current state"""
        # Strip ANSI codes before adding
        clean_msg = strip_ansi_codes(msg)
        log_buffer.append(clean_msg)
        return "\n".join(log_buffer)

    def should_log_line(line):
        """Determine if a line should be logged (errors, warnings, important info only)"""
        line_lower = line.lower()
        # Log errors, warnings, and important milestones
        if any(
            keyword in line_lower
            for keyword in [
                "error",
                "fail",
                "warn",
                "abort",
                "exception",
                "complete",
                "success",
                "registered",
                "extracting features",
                "matching features",
                "sparse reconstruction",
                "dense reconstruction",
                "frames extracted",
                "building",
                "exporting",
                "undistorting",
            ]
        ):
            return True
        # Log lines with [INFO], [ERROR], [WARN] tags
        if any(tag in line for tag in ["[INFO]", "[ERROR]", "[WARN]"]):
            return True
        return False

    try:
        # Validate inputs
        if not video_file:
            yield "Error: No video file uploaded", None
            return

        if not project_dir or not project_dir.strip():
            yield "Error: Project directory name cannot be empty", None
            return

        if fps <= 0:
            yield "Error: FPS must be greater than 0", None
            return

        # Clean project directory name
        project_dir = project_dir.strip().replace(" ", "_")
        project_dir = "".join(c for c in project_dir if c.isalnum() or c in "_-")

        # Create output directory
        output_base = Path("output")
        output_base.mkdir(exist_ok=True)

        yield add_log("🎬 Starting video processing pipeline..."), None
        yield add_log(f"📁 Project: {project_dir}"), None
        yield add_log(f"🎞️  FPS: {fps}"), None
        yield add_log(f"📹 Video: {video_file}"), None
        yield add_log("=" * 60), None

        progress(0.1, desc="Starting COLMAP pipeline...")

        # Set environment variables
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        env["COLMAP_NO_GPU"] = "1"

        # Step 1: Run COLMAP pipeline with minimal logging
        yield add_log("\n🔄 STEP 1: Running COLMAP Pipeline"), None
        yield add_log("-" * 60), None
        yield add_log("ℹ️  Only showing important messages to prevent lag"), None
        yield add_log("ℹ️  Heartbeat every 30s to confirm it's running"), None
        yield add_log(""), None

        colmap_cmd = ["./pipeline_colmap.sh", video_file, project_dir, str(fps)]

        # Run COLMAP with selective output
        process = subprocess.Popen(
            colmap_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )

        line_count = 0
        last_update_time = time.time()

        if process.stdout:
            for line in iter(process.stdout.readline, ""):
                if line:
                    line_count += 1
                    # Log only important lines
                    if should_log_line(line):
                        yield add_log(line.rstrip()), None
                        last_update_time = time.time()
                    # Heartbeat every 30 seconds to show it's alive
                    elif time.time() - last_update_time > 30:
                        yield add_log(
                            f"⏳ Processing... ({line_count} operations)"
                        ), None
                        last_update_time = time.time()

            process.stdout.close()

        return_code = process.wait()

        if return_code != 0:
            yield add_log(f"\n❌ COLMAP failed with exit code {return_code}"), None
            return

        yield add_log("\n✅ COLMAP pipeline completed!"), None
        yield add_log("=" * 60), None

        progress(0.4, desc="Starting LichtFeld-Studio...")

        # Step 2: Run LichtFeld-Studio with minimal logging
        yield add_log("\n🔄 STEP 2: Running LichtFeld-Studio"), None
        yield add_log("-" * 60), None
        yield add_log("⚠️  GUI window will open - train and close when done"), None
        yield add_log(""), None

        lichtfeld_cmd = [
            "./build/LichtFeld-Studio",
            "-d",
            project_dir,
            "-o",
            f"output/{project_dir}",
            "--gut",
        ]

        process = subprocess.Popen(
            lichtfeld_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )

        line_count = 0
        last_update_time = time.time()

        if process.stdout:
            for line in iter(process.stdout.readline, ""):
                if line:
                    line_count += 1
                    if should_log_line(line):
                        yield add_log(line.rstrip()), None
                        last_update_time = time.time()
                    elif time.time() - last_update_time > 30:
                        yield add_log(f"⏳ Training... ({line_count} operations)"), None
                        last_update_time = time.time()

            process.stdout.close()

        return_code = process.wait()

        # Check if training actually completed successfully before the crash
        training_completed = any(
            "training completed successfully" in line.lower() for line in log_buffer
        )

        # Exit code -11 is SIGSEGV (segfault), often happens when closing GUI with X
        # If training completed successfully, treat this as success
        if return_code == -11 and training_completed:
            yield add_log(
                "\n⚠️  GUI closed with segfault (exit -11), but training completed successfully"
            ), None
            yield add_log("✅ Treating as successful completion"), None
        elif return_code != 0:
            yield add_log(
                f"\n❌ LichtFeld-Studio failed with exit code {return_code}"
            ), None
            return

        yield add_log("\n✅ LichtFeld-Studio completed!"), None
        yield add_log("=" * 60), None

        progress(0.7, desc="Creating archive...")

        # Step 3: Create zip file
        yield add_log("\n🔄 STEP 3: Creating Download Archive"), None
        yield add_log("-" * 60), None

        zip_filename = f"{project_dir}_output.zip"
        zip_path = Path("output") / zip_filename

        file_count = 0
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            project_path = Path(project_dir)
            if project_path.exists():
                for file in project_path.rglob("*"):
                    if file.is_file():
                        arcname = file.relative_to(project_path.parent)
                        zipf.write(file, arcname)
                        file_count += 1
                        if file_count % 100 == 0:
                            yield add_log(f"  Archived {file_count} files..."), None

            output_path = Path("output") / project_dir
            if output_path.exists():
                for file in output_path.rglob("*"):
                    if file.is_file():
                        arcname = file.relative_to(output_path.parent)
                        zipf.write(file, f"output/{arcname}")
                        file_count += 1
                        if file_count % 100 == 0:
                            yield add_log(f"  Archived {file_count} files..."), None

        yield add_log(f"\n✅ Archive created: {file_count} files"), None
        progress(1.0, desc="Complete!")

        # Final summary
        yield add_log("\n" + "=" * 60), None
        yield add_log("🎉 PROCESSING COMPLETE!"), None
        yield add_log("=" * 60), None
        yield add_log("\n📊 Summary:"), None
        yield add_log(f"  Project: {project_dir}"), None
        yield add_log(f"  Total files: {file_count}"), None

        # List some generated files
        if project_path.exists():
            files = [f for f in project_path.rglob("*") if f.is_file()]
            yield add_log(f"\n📁 {project_dir}/ ({len(files)} files)"), None
            for file in sorted(files)[:3]:
                yield add_log(f"  - {file.relative_to(project_path.parent)}"), None
            if len(files) > 3:
                yield add_log(f"  ... and {len(files) - 3} more"), None

        if output_path.exists():
            ply_files = [f for f in output_path.rglob("*.ply")]
            if ply_files:
                yield add_log(f"\n📦 PLY files: {len(ply_files)}"), None
                for file in sorted(ply_files)[:3]:
                    yield add_log(f"  - {file.name}"), None
                if len(ply_files) > 3:
                    yield add_log(f"  ... and {len(ply_files) - 3} more"), None

        yield add_log(f"\n💾 Download: {zip_filename}"), None
        yield add_log("=" * 60), None

        yield "\n".join(log_buffer), str(zip_path)

    except Exception as e:
        yield add_log(f"\n❌ Error: {str(e)}"), None


def create_interface():
    """Create and configure the Gradio interface."""

    with gr.Blocks(
        title="LichtFeld-Studio Video Processor", theme=gr.themes.Soft()
    ) as app:
        gr.Markdown(
            """
            # 🎥 LichtFeld-Studio Video Processor
            
            Process videos through the LichtFeld-Studio pipeline to generate 3D reconstructions.
            
            ### Pipeline Steps:
            1. **COLMAP Pipeline**: Extracts frames and runs COLMAP reconstruction
            2. **LichtFeld-Studio**: Opens GUI for training and model generation
            3. **Output**: Downloads all generated files (including PLY files)
            """
        )

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 📋 Input Configuration")

                video_input = gr.File(
                    label="Video File", file_types=["video"], file_count="single"
                )

                project_dir_input = gr.Textbox(
                    label="Project Directory Name",
                    placeholder="e.g., my_reconstruction",
                    value="reconstruction_project",
                )

                fps_input = gr.Number(
                    label="Frames Per Second (FPS)",
                    value=2,
                    minimum=0.1,
                    maximum=60,
                    step=0.1,
                )

                process_btn = gr.Button(
                    "🚀 Start Processing", variant="primary", size="lg"
                )

            with gr.Column(scale=1):
                gr.Markdown("### 📊 Processing Status")

                status_output = gr.Textbox(
                    label="Status (Important messages only)",
                    lines=25,
                    max_lines=30,
                    interactive=False,
                    autoscroll=True,
                )

                download_output = gr.File(label="Download Results", interactive=False)

        gr.Markdown(
            """
            ---
            ### ℹ️ Instructions:
            1. Upload your video file (MP4, MOV, AVI, etc.)
            2. Enter a unique project directory name
            3. Set the FPS for frame extraction (lower = fewer frames, faster)
            4. Click "Start Processing"
            5. Monitor the status - you'll see important milestones and errors only
            6. Heartbeat messages every 30s confirm the process is still running
            7. LichtFeld-Studio GUI will open - train and close when done
            8. Download the zip file with all generated data
            
            **Note**: Only critical messages are shown to prevent lag. If no updates for >30s, check the heartbeat.
            """
        )

        # Connect button to processing function
        process_btn.click(
            fn=process_video,
            inputs=[video_input, project_dir_input, fps_input],
            outputs=[status_output, download_output],
        )

    return app


if __name__ == "__main__":
    app = create_interface()
    app.launch(server_name="0.0.0.0", server_port=7860, share=True, show_error=True)
